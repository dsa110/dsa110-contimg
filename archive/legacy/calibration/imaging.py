from typing import Optional, Union

from casatasks import tclean as casa_tclean


def quick_image(
    ms: str,
    imagename: str,
    field: str,
    niter: int = 1000,
    threshold: str = "0.1mJy",
    weighting: str = "briggs",
    robust: float = 0.5,
    cell: Union[str, list] = "3arcsec",
    imsize: Optional[int] = None,
) -> None:
    casa_tclean(
        vis=ms,
        imagename=imagename,
        field=field,
        deconvolver="multiscale",
        scales=[0, 3, 10],
        weighting=weighting,
        robust=robust,
        niter=niter,
        threshold=threshold,
        cell=cell,
        imsize=imsize,
        usemask="auto-multithresh",
        interactive=False,
    )


