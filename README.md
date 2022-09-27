![unit tests](https://github.com/michael-pruglo/aesthetics/actions/workflows/python-app.yml/badge.svg)

# aesthetics battle royale

Exploration of personal style. Provided a media library with metadata - explore, rate, tag, use DL.

## Run:

Run gui app with

```bash
python src/ae_rater.py [path/to/media]
```

Run tests with
```bash
python -m unittests
```

## Architecture

```
|--------------|    |---------------|
|  ae_rater    | -> | ae_rater_view |
| (controller) |    |    (view)     |
|--------------|    |---------------|
      |
      V
|----------------|    |-----------------|
| ae_rater_model | -> | rating_backends |
|     (model)    |    | (ELO, Glicko..) |
|----------------|    |-----------------|
      |
      V
|-------------|
| db_managers |
|-------------|
      |
      V
|-------------|
| metadata.py |
| (read/write |
|  metadata   |
|  on disk)   |
|-------------|
```

## TODO

- improve performance
- add megaboosts


