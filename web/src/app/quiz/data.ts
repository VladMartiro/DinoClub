/* The website reads the same JSON the Python package audits. One source of
   truth: edit src/dinoclub/quiz/data/mini/*.json and both sides see it.
   `dino-quiz-audit --dataset mini` is the place to check an edit. */
import spaceJson from '../../../../src/dinoclub/quiz/data/mini/traits.json';
import dinosaursJson from '../../../../src/dinoclub/quiz/data/mini/dinosaurs.json';
import questionsJson from '../../../../src/dinoclub/quiz/data/mini/questions.json';

import { Dinosaur, Engine, Question, TraitSpaceData } from './engine';

export const DATASET = 'mini';

export function loadEngine(): Engine {
  return new Engine(
    spaceJson as TraitSpaceData,
    dinosaursJson.dinosaurs as Dinosaur[],
    questionsJson.questions as Question[],
  );
}
