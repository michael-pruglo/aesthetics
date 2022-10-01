![unit tests](https://github.com/michael-pruglo/aesthetics/actions/workflows/python-app.yml/badge.svg)

# aesthetics battle royale

Exploration of personal style. Provided a media library with metadata - explore, rate, tag, use DL.

## Run:

### Run gui app with

```bash
python src/ae_rater.py [path/to/media] [n_cards=2]
```
Where `n_cards` is the number of participants in one match (increase efficiency of rating). <br>
If `n_cards > 2` then you have to supply results in a string form. Each participant has it's own id letter (a,b,c,...). The result string consists of words separated by whitespace. Each word represents a tier, starting from the winners. <br>
For example:

```
f ea cb d
```
means that the media with id `f` is the strongest, `e` and `a` tie for the second place, `c` and `b` tie for the third place, and `d` is the weakest.

This language also allows for boosts. Follow the letter with `+` n times to give that profile n boosts.<br>
For example:

```
d++c a+ b
```
Will give 2 boosts to `d`, one boost to `a`, and then processed as `dc a b`



### Run tests with
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


