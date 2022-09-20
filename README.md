# aesthetics battle royale

Exploration of personal style. Provided a media library with metadata - explore, rate, tag, use DL.

Run with:

```py
python src/ae_rater.py [path/to/media]
```

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

- add glicko math
- fix bug: boost increases nmatches
- add tests
- change visualization of rating in ProfileCard from ugly dicts

