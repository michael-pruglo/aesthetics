![unit tests](https://github.com/michael-pruglo/aesthetics/actions/workflows/python-app.yml/badge.svg)

# aesthetics battle royale

Exploration of personal style. Provided a media library with metadata - explore, rate, tag, use DL.

## Run

```bash
$ src/ae_rater.py --help
usage: ae_rater.py [-h] [-r] [-p {default,fresh,top}] [-s] [media_dir] [num_participants]

positional arguments:
  media_dir             media folder to operate on
  num_participants      number of participants in MATCH mode

optional arguments:
  -h, --help            show this help message and exit
  -r, --refresh         refresh db to incorporate folder updates
  -p {default,fresh,top}, --prioritizer {default,fresh,top}
                        which media is prioritized for matches
  -s, --search          run SEARCH instead of MATCH mode
```

### Run tests with

```bash
[SKIPLONG=1] python -m unittests
```

## Outcome language

If `num_participants > 2` then you have to supply results in a string form. Each participant has it's own id letter (a,b,c,...). The result string consists of words separated by whitespace. Each word represents a tier, starting from the winners. <br>
For example:

```
f ea cb d
```
means that the media with id `f` is the strongest, `e` and `a` tie for the second place, `c` and `b` tie for the third place, and `d` is the weakest.

This language also allows for manual change of rating, independent of matches. Follow the letter with `+` n times to give that profile n boosts, and use `-` n times to decrease the rating. If you're feeling adventurous you can even mix the two!<br>
For example:

```
d+++c a- b
```
Will give 3 boosts to `d`, one decrease to `a`, and then process `dc a b`

Click on tags to open the Meta Manager and change tags/stars on disk. You will even get suggestions from AI!<br>
Click on any media to open the full version in an external program

## Note

simple CNN didn't learn rating from imgs or tags
random forest from tags didn't learn rating
tried using nearest neighbors to predict rating from tags, got sqrt(mse)=600

## TODO

### short-term

- make history replays
    - after the replays are done, compare different ratsystems on the task of predicting outcomes - NOTE that we have to start from the same initial point to compare
- learn how to convert webp and other unsupported formats right with yt-dlp
- group similar items, finding balance between two crucial points:
  a: avoid oversaturation of close things
  b: but simultaneously preserve the important differences/elements
  ideas:
    - maybe create an unrated folder with all the possible variations - to help ML - violates 'b'
    - maybe combine into groups, and rate/compare/meta the whole group - violates 'b'
      would be cool to have general meta shared by the group and some unique for each media
- add PARANOID version - with extensive checks/asserts, and FAST - with no checks
- add more tests for downloaders
- plot a couple of "surprise" metrics and follow it overtime - how well the current ratings predict current matches. As a metric for convergence to true ratings
  - average Glicko rd
  - ELO/Glicko MSE expected results/real results
  - sum of absolute changes to ratings
- polish dataset
  - add health checkers:
    - corellation between rankings: stars/Glicko/ELO

### long-term

- improve performance
- improve tag suggestions and auto-label lower priority media
- learn to predict rating
- scrape web for new media, predict ratings and show the most promising candidates
  - scrape reverse-search img from the higest rated
- learn the overall/specific styles and generate new media with smth like stable diffusion
