/* The website reads the same JSON the Python package audits. One source of
   truth: edit src/dinoclub/quiz/data/full/*.json and both sides see it.
   `dino-quiz-audit --dataset full` is the place to check an edit. */
import spaceJson from '../../../../src/dinoclub/quiz/data/full/traits.json';
import dinosaursJson from '../../../../src/dinoclub/quiz/data/full/dinosaurs.json';
import questionsJson from '../../../../src/dinoclub/quiz/data/full/questions.json';

import { Dinosaur, Engine, Question, TraitSpaceData } from './engine';

export const DATASET = 'full';

export function loadEngine(): Engine {
  return new Engine(
    spaceJson as TraitSpaceData,
    dinosaursJson.dinosaurs as Dinosaur[],
    questionsJson.questions as Question[],
  );
}
