![unit tests](https://github.com/michael-pruglo/aesthetics/actions/workflows/python-app.yml/badge.svg)

# aesthetics exploration

Provided a media library with metadata - explore, rate, tag, use DL.


## Note

simple CNN didn't learn rating from imgs or tags
random forest from tags didn't learn rating
tried using nearest neighbors to predict rating from tags, got sqrt(mse)=600

## TODO

### short-term

- group similar items, finding balance between two crucial points:
  a: avoid oversaturation of close things
  b: but simultaneously preserve the important differences/elements
  ideas:
    - maybe create an unrated folder with all the possible variations - to help ML - violates 'b'
    - maybe combine into groups, and rate/compare/meta the whole group - violates 'b'
      would be cool to have general meta shared by the group and some unique for each media
- polish dataset
  - add health checkers:
    - corellation between rankings: stars/Glicko/ELO

### long-term

- improve performance
- learn to predict rating
- scrape web for new media, predict ratings and show the most promising candidates
  - scrape reverse-search img from the higest rated
- learn the overall/specific styles and generate new media with smth like stable diffusion
