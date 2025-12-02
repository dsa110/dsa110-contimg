# How-To: Build a Nightly Mosaic

Plan and build a mosaic from recent `*.image.pbcor` tiles.

```
python -m dsa110_contimg.mosaic.cli plan --products-db state/db/products.sqlite3   --name night_YYYY_MM_DD --since <epoch> --until <epoch>
python -m dsa110_contimg.mosaic.cli build --products-db state/db/products.sqlite3   --name night_YYYY_MM_DD --output /data/ms/mosaics/night_YYYY_MM_DD.img
```
