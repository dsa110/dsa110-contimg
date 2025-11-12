"""uvx: I/O tools for UVX data."""

import h5py
import numpy as np
import pandas as pd
import xarray as xp
from astropy.coordinates import EarthLocation
from astropy.time import Time
from loguru import logger

import ska_ost_low_uv
from ska_ost_low_uv.datamodel.phase_center import PhaseCenter
from ska_ost_low_uv.datamodel.uvx import UVX
from ska_ost_low_uv.utils import get_resource_path, load_yaml


def write_uvx(uv: UVX, filename: str):
    """Write a aavs UV object to a HDF5 file.

    Args:
        uv (UVX): ska_ost_low_uv.datamodel.UV object
        filename (str): name of output file
    """
    # Load UVX schema from YAML. We can use this to load descriptions
    # And other metadata from the schema (e.g. dimensions)
    uvx_schema = load_yaml(get_resource_path('datamodel/uvx.yaml'))

    def _str2bytes(darr):
        if isinstance(darr, str):
            darr = np.array(darr)
        if 'U' in str(darr.dtype) or 'obj' in str(darr.dtype):
            return darr.astype('bytes')
        else:
            return darr

    def _set_attrs(dobj, dset):
        for k, v in dobj.attrs.items():
            try:
                dset.attrs[k] = v
            except TypeError:
                dset.attrs[k] = v.astype('bytes')

    def _create_dset(group, name, dobj):
        data = _str2bytes(dobj)
        dset = group.create_dataset(name, data=data)
        _set_attrs(dobj, dset)

    with h5py.File(filename, mode='w') as h:
        # Basic metadata
        h.attrs['CLASS'] = 'AA_UV'
        h.attrs['VERSION'] = ska_ost_low_uv.__version__
        h.attrs['name'] = uv.name

        ####################
        # VISIBILITY GROUP #
        ####################
        g_vis = h.create_group('visibilities')
        g_vis_c = g_vis.create_group('coords')

        _create_dset(g_vis, 'data', uv.data)

        # Time
        g_vis_time = g_vis['coords'].create_group('time')
        for coord in ('mjd', 'lst', 'unix'):
            _create_dset(g_vis_time, coord, uv.data.coords[coord])

        _set_attrs(uv.data.time, g_vis_time)

        # Baseline
        g_vis_bl = g_vis['coords'].create_group('baseline')
        for coord in ('ant1', 'ant2'):
            _create_dset(g_vis_bl, coord, uv.data.coords[coord])

        # Freq & polarization
        for coord in ('polarization', 'frequency'):
            _create_dset(g_vis_c, coord, uv.data.coords[coord])

        #################
        # ANTENNA GROUP #
        #################
        # fmt: off
        g_ant   = h.create_group('antennas')
        g_ant_c = g_ant.create_group('coords')
        g_ant_a = g_ant.create_group('attrs')

        for dset_name in ('enu', 'ecef'):
            _create_dset(g_ant, dset_name, uv.antennas[dset_name])

        for coord in ('antenna', 'spatial'):
            _create_dset(g_ant_c, coord, uv.antennas.coords[coord])

        for attr in (
            'identifier',
            'flags',
            'array_origin_geocentric',
            'array_origin_geodetic',
            'array_rotation_angle'
        ):
            _create_dset(g_ant_a, attr, uv.antennas.attrs[attr])
        # fmt: on

        ################
        # PHASE CENTER #
        ################
        # fmt: off
        g_pc    = h.create_group('phase_center')
        pc      = uv.phase_center.icrs
        ra, dec = pc.ra.to('hourangle'), pc.dec.to('deg')
        if pc.isscalar:
            ra, dec = np.expand_dims(ra, 0), np.expand_dims(dec, 0)

        d_pc_ra  = g_pc.create_dataset('ra', data=ra)
        d_pc_dec = g_pc.create_dataset('dec', data=dec)
        d_pc_ra.attrs['unit']  = 'hourangle'
        d_pc_dec.attrs['unit'] = 'deg'
        # fmt: on

        ########################
        # PROVENANCE / CONTEXT #
        ########################

        g_prov = h.create_group('provenance')
        for k, v in uv.provenance.items():
            if isinstance(v, dict):
                g_prov_a = g_prov.create_group(k)
                for sk, sv in v.items():
                    g_prov_a.attrs[sk] = sv
            else:
                g_prov.attrs[k] = v

        g_cont = h.create_group('context')
        for k, v in uv.context.items():
            if isinstance(v, dict):
                g_cont_a = g_cont.create_group(k)
                for sk, sv in v.items():
                    g_cont_a.attrs[sk] = sv
            else:
                g_cont.attrs[k] = v

        # add metadata about phasing (or lack of)
        h['phase_center'].attrs['phase_type'] = uv.phase_center.phase_type
        h['phase_center'].attrs['source_name'] = uv.phase_center.name

        h['visibilities'].attrs['phase_center_tracking_applied'] = False

        # Add descriptions from uvx.yaml schema
        for k, v in uvx_schema.items():
            k = k.replace('uvx/', '')  # Strip uvx/ prefix to get hdf5 path
            if k in h.keys():
                if 'description' in v.keys():
                    h[k].attrs['description'] = v['description']
                if 'dims' in v.keys():
                    # Convert dims into a string
                    h[k].attrs['dims'] = str(tuple(v['dims']))
                if 'unit' in v.keys():
                    h[k].attrs['unit'] = v['unit']
            else:
                logger.warning(f'Could not find {k} in HDF5 file: {list(h.keys())}')


def read_uvx(filename: str) -> UVX:
    """Load ska_ost_low_uv UVX object from uvx (HDF5) file.

    Args:
        filename (str): path to uvx file, or h5py.File

    Returns:
        uv (ska_ost_low_uv.datamodel.UV): UV object
    """
    # Load UVX schema from YAML. We can use this to load descriptions
    # And other metadata from the schema (e.g. dimensions)
    uvx_schema = load_yaml(get_resource_path('datamodel/uvx.yaml'))

    def _to_list(lstr):
        return [x.strip("'").strip() for x in lstr.strip('()[]').split(', ')]

    if isinstance(filename, h5py.File):
        fh = filename
    else:
        fh = h5py.File(filename, mode='r')

    with fh as h:
        ################
        # ANTENNA DSET #
        ################
        coords = {
            'antenna': h['antennas']['coords']['antenna'][:],
            'spatial': h['antennas']['coords']['spatial'][:].astype('str'),
        }

        data_vars = {
            'enu': xp.DataArray(
                h['antennas']['enu'],
                dims=_to_list(h['antennas']['enu'].attrs['dims']),
                attrs=dict(h['antennas']['enu'].attrs.items()),
                coords=coords,
            ),
            'ecef': xp.DataArray(
                h['antennas']['ecef'],
                dims=_to_list(h['antennas']['ecef'].attrs['dims']),
                attrs=dict(h['antennas']['ecef'].attrs.items()),
                coords=coords,
            ),
        }

        attrs = {
            'identifier': xp.DataArray(
                h['antennas/attrs/identifier'][:].astype('str'),
                dims=('antenna'),
                attrs=dict(h['antennas/attrs/identifier'].attrs.items()),
            ),
            'flags': xp.DataArray(
                h['antennas/attrs/flags'][:],
                dims=('antenna'),
                attrs=dict(h['antennas/attrs/flags'].attrs.items()),
            ),
            'array_origin_geocentric': xp.DataArray(
                h['antennas/attrs/array_origin_geocentric'][:],
                dims=('spatial'),
                attrs=dict(h['antennas/attrs/array_origin_geocentric'].attrs.items()),
            ),
            'array_origin_geodetic': xp.DataArray(
                h['antennas/attrs/array_origin_geodetic'][:],
                dims=('spatial'),
                attrs=dict(h['antennas/attrs/array_origin_geodetic'].attrs.items()),
            ),
        }

        try:
            attrs['array_rotation_angle'] = xp.DataArray(
                h['antennas/attrs/array_rotation_angle'],
                attrs=dict(h['antennas/attrs/array_rotation_angle'].attrs.items()),
            )
        except KeyError:
            rot_attrs = uvx_schema['uvx/antennas/attrs/array_rotation_angle']
            attrs['array_rotation_angle'] = xp.DataArray(
                0.0,
                attrs={
                    'units': rot_attrs['units'],
                    'description': rot_attrs['description'],
                },
            )

        antennas = xp.Dataset(data_vars=data_vars, coords=coords, attrs=attrs)

        # Small bytes -> string fixup
        antennas.attrs['array_origin_geodetic'].attrs['units'] = (
            antennas.attrs['array_origin_geodetic'].attrs['units'].astype('str')
        )

        ################
        # VISIBILITIES #
        ################

        # Coordinate - time
        # fmt: off
        mjd     = h['visibilities/coords/time/mjd'][:]
        lst     = h['visibilities/coords/time/lst'][:]
        unix    = h['visibilities/coords/time/unix'][:]
        t_coord = pd.MultiIndex.from_arrays(
            (mjd, lst, unix), names=('mjd', 'lst', 'unix')
        )
        # fmt: on

        # Coordinate - baseline
        bl_coord = pd.MultiIndex.from_arrays(
            (
                h['visibilities/coords/baseline/ant1'][:],
                h['visibilities/coords/baseline/ant2'][:],
            ),
            names=('ant1', 'ant2'),
        )

        # Coordinate - polarization
        pol_coord = h['visibilities/coords/polarization'][:].astype('str')

        # Coordinate - frequency
        f_center = h['visibilities/coords/frequency'][:]
        f_coord = xp.DataArray(
            f_center,
            dims=('frequency',),
            attrs=dict(h['visibilities/coords/frequency'].attrs.items()),
        )

        coords = {
            'time': t_coord,
            'polarization': pol_coord,
            'baseline': bl_coord,
            'frequency': f_coord,
        }

        vis = xp.DataArray(
            h['visibilities']['data'],
            coords=coords,
            dims=_to_list(h['visibilities']['data'].attrs['dims']),
        )
        for k, v in h['visibilities'].attrs.items():
            vis.attrs[k] = v

        # Copy over attributes
        for c in coords.keys():
            for k, v in h[f'visibilities/coords/{c}'].attrs.items():
                vis.coords[c].attrs[k] = v

        ################
        # PHASE CENTER #
        ################
        phase_center = PhaseCenter(
            h['phase_center']['ra'][:],
            h['phase_center']['dec'][:],
            unit=(
                h['phase_center']['ra'].attrs['unit'],
                h['phase_center']['dec'].attrs['unit'],
            ),
            phase_type=h['phase_center'].attrs['phase_type'],
            name=h['phase_center'].attrs['source_name'],
        )

        ########################
        # PROVENANCE / CONTEXT #
        ########################
        provenance = dict(h['provenance'].attrs.items())
        for k, v in h['provenance'].items():
            provenance[k] = dict(v.attrs.items())

        context = dict(h['context'].attrs.items())
        for k, v in h['context'].items():
            context[k] = dict(v.attrs.items())

        # Add time and earth location
        eloc = EarthLocation.from_geocentric(
            *h['antennas']['attrs']['array_origin_geocentric'][:],
            unit=h['antennas']['attrs']['array_origin_geocentric'].attrs['units'],
        )
        t = Time(unix, format='unix', location=eloc)

        uv = UVX(
            name=h.attrs['name'],
            antennas=antennas,
            context=context,
            data=vis,
            timestamps=t,
            origin=eloc,
            phase_center=phase_center,
            provenance=provenance,
        )

    return uv
