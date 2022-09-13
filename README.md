# aesthetics battle royale

Exploration of personal style. Provided a media library with metadata, explore, rate, tag, use DL.

Main script in `elo_rater.py`

```
|--------------|    |----------|
|  elo_rater   | -> | elo_view |
| (controller) |    |  (view)  |
|--------------|    |----------|
      |
      V
|-----------|
| elo_model |
| (model)   |
|-----------|
      |
      V
|-------------|
| metadata.py |
| (database)  |
|-------------|
```

