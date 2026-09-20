"""Dino Club: a dinosaur personality test, and a movie recommender.

Two related systems, deliberately kept separate because they answer different
questions in different spaces:

  dinoclub.quiz       Which dinosaur are you?  Four behavioral trait axes
                      scored from -5 to +5, matched by Euclidean distance.

  dinoclub.recommend  What should you watch?  Ten movie-taste axes scored
                      from 0 to 1, with an adaptive question policy.

The quiz is the front door. The recommender is phase two.
"""

__version__ = "0.2.0"
