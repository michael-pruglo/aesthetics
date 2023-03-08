import math
import os
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor

from db_managers import MetadataManager
from ai_types import StarPredictorBackend


class StarPredictorBaseline(StarPredictorBackend):
  def predict_from_tags(self, tags):
    AVERAGE = 1.8
    return AVERAGE


def r_mse(pred, y):
  return round(math.sqrt(((pred-y)**2).mean()), 6)


class RandomForest(StarPredictorBackend):
  def __init__(self):
    super().__init__()

    def prepare_datasets():
      MEDIAPATH = os.path.abspath("")
      mm = MetadataManager(MEDIAPATH)
      train_df = mm.get_db().reset_index().rename(columns={'index':'name'})
      train_df = train_df[['name', 'tags', 'stars']]
      vocab = train_df['tags'].str.split().explode().unique()
      tags_df = pd.DataFrame({tag:train_df['tags'].str.contains(tag,regex=False) for tag in vocab})
      train_df = pd.concat([train_df, tags_df], axis=1)
      valid_df = train_df.sample(frac=0.1)
      train_df.drop(valid_df.index, inplace=True)
      valid_df.sort_values('stars', ascending=False, inplace=True)
      return train_df, valid_df, vocab

    train_df, valid_df, self.vocab = prepare_datasets()
    print("Datasets are prepared.\n"
          f"vocab has {len(self.vocab)} items: {self.vocab[:10]}...\n"
          f"train_df has {len(train_df)} and valid has {len(valid_df)}\n"
          f"train_df:\n{train_df.sample(5)}\n"
          f"valid_df:\n{valid_df.sample(5)}\n")
    train_x, train_y = train_df[self.vocab], train_df['stars']
    valid_x, valid_y = valid_df[self.vocab], valid_df['stars']
    self.forest = RandomForestRegressor(oob_score=True)
    self.forest.fit(train_x, train_y)

    def loss(x, y):
      return r_mse(self.forest.predict(x), y)
    print( "Random forest trained. MSE:\n"
          f" test={loss(train_x, train_y)}\n"
          f"valid={loss(valid_x, valid_y)}\n"
          f"  oob={r_mse(self.forest.oob_prediction_, train_y)}")
    plt.plot(valid_y.index, valid_y)
    plt.plot(valid_y.index, self.forest.predict(valid_x))
    plt.show()


  def predict_from_tags(self, tags):
    pred = self.forest.predict(pd.DataFrame({t:[t in tags] for t in self.vocab}))
    assert len(pred) == 1
    return pred[0]


if __name__ == "__main__":
  rf = RandomForest()
