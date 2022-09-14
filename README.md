# aesthetics battle royale

Exploration of personal style. Provided a media library with metadata, explore, rate, tag, use DL.

Run with:
```py
python src/elo_rater.py [path/to/media]
```

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

## TODO:
- add middle column listing all participants sorted: top...first...second...
- add glicko math
- save entire match history into csv  name1,name2,{-1|0|1}

