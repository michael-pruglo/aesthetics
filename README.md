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

This language also allows for manual change of rating, independent of matches. Follow the letter with `+` n times to give that profile n boosts, and use `-` n times to decrease the rating. If you're feeling adventurous you can even mix the two!<br>
For example:

```
d++c a- b
```
Will give 2 boosts to `d`, one decrease to `a`, and then process `dc a b`


Click on tags to open the Meta Manager and change tags/stars on disk. You will even get suggestions from AI!<br>
Click on any media to open the full version in an external program

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
- add browser: filtering, sort by rating
- learn to predict rating
- scrape web for new media, predict ratings and show the most promising candidates
- improve tag suggestions and auto-label lower priority media
- learn the overall/specific styles and generate new media with smth like stable diffusion
- use nearest neighbor search to find similar already rated items, and derive rating/tags from that
