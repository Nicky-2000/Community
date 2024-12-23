import numpy as np
import matplotlib.pyplot as plt
import random
import os
import signal
import sys
from functools import partial
import multiprocessing

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import torch
import torch.nn as nn
import torch.nn.functional as F


MAX_GENERATIONS = 10
POP_SIZE = 100
TURNS = 500
CIVILIANS = 40
HIDDEN_SIZE = 40
TASK_FEATURE_SIZE = 7
PLAYER_STATE_SIZE = 11


if __name__ == "__main__" or __name__ == "__mp_main__":
    from run import run
else:
    from teams.team_2.training.run import run


def handle_signal(best_model):
    def catch_signal(sig, frame):
        print(f"\nCaught {signal.Signals(sig).name}, saving best model...")

        best_score = evaluate_fitness(*best_model, turns=TURNS, civilians=CIVILIANS)
        print(f"best_model: {best_score} per turn per civilian")
        torch.save(
            best_model[0].state_dict(),
            f"best_task_score={str(round(best_score,3)).replace('.', ',')}.pth",
        )
        torch.save(
            best_model[1].state_dict(),
            f"best_rest_score={str(round(best_score, 3)).replace('.', ',')}.pth",
        )
        sys.exit(0)

    return catch_signal


class TaskScorerNN(nn.Module):
    def __init__(self, task_feature_size, player_state_size, hidden_size):
        super(TaskScorerNN, self).__init__()
        self.fc1 = nn.Linear(task_feature_size + player_state_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size // 2)
        self.fc3 = nn.Linear(hidden_size // 2, 1)  # Outputs a single score for a task

    def forward(self, task_features: torch.Tensor, player_state: torch.Tensor):
        # Concatenate task features and player state
        combined = torch.cat(
            [
                task_features if task_features.ndim > 1 else task_features.view(-1),
                player_state,
            ],
            dim=-1,
        )
        x = F.relu(self.fc1(combined))
        x = F.relu(self.fc2(x))
        score = self.fc3(x)  # Outputs score
        return score


class RestDecisionNN(nn.Module):
    def __init__(self, input_size, hidden_size):
        super(RestDecisionNN, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.fc2 = nn.Linear(hidden_size, hidden_size // 2)
        self.fc3 = nn.Linear(hidden_size // 2, 1)  # Single output for rest score

    def forward(self, features):
        x = F.relu(self.fc1(features))
        x = self.fc2(x)
        score = self.fc3(x)
        return score


def evaluate_fitness(task_model: nn.Module, rest_model: nn.Module, turns, civilians):
    tasks = run(task_model, rest_model, turns, civilians)
    score = tasks / turns / civilians
    print(f"score: {round(score, 3)}")
    return score


def crossover(parent1, parent2, is_task):
    if is_task:
        child = TaskScorerNN(TASK_FEATURE_SIZE, PLAYER_STATE_SIZE, HIDDEN_SIZE)
    else:
        child = RestDecisionNN(PLAYER_STATE_SIZE + 1, HIDDEN_SIZE)

    for param1, param2, child_param in zip(
        parent1.parameters(), parent2.parameters(), child.parameters()
    ):
        child_param.data.copy_((param1.data + param2.data) / 2)  # Weighted average
    return child


def mutate(model, mutation_rate=0.1, mutation_noise=0.01):
    for param in model.parameters():
        if torch.rand(1).item() < mutation_rate:
            param.data += (
                torch.randn_like(param.data) * mutation_noise
            )  # Small random noise


def select_parents(population, fitness_scores):
    best = sorted(
        list(zip(population, fitness_scores)), key=lambda x: x[1], reverse=True
    )

    return [b[0] for b in best][: len(population) // 2]


def task_scorer():
    pass


def rest_scorer():
    pass


class Task:
    def __init__(self, features: torch.Tensor, state=None):
        self.features = features
        self.state = state
        if not state:
            self.state = torch.zeros(features.shape[0])


def plot(avg_scores, max_scores):
    # Get the current working directory (runfolder)
    runfolder = os.getcwd()

    # Plot both curves
    plt.plot(
        np.arange(len(avg_scores)), avg_scores, label="Average Score", color="blue"
    )
    plt.plot(np.arange(len(max_scores)), max_scores, label="Max Score", color="red")

    # Add labels and title
    plt.xlabel("Generation")
    plt.ylabel("Score")
    plt.title(
        f"Average and Max Fitness Scores Over {MAX_GENERATIONS} Generations\nInitial population size = {POP_SIZE}"
    )

    # Add a legend
    plt.legend()

    # Save the plot to the current directory
    plt.savefig(os.path.join(runfolder, "fitness_scores.png"))
    print("path", os.path.join(runfolder, "fitness_scores.png"))


if __name__ == "__main__":
    avg_scores = []
    max_scores = []

    parents = []
    offspring = []
    fitness_scores = []
    population = [
        (
            TaskScorerNN(TASK_FEATURE_SIZE, PLAYER_STATE_SIZE, HIDDEN_SIZE),
            # 1 is hardcoded
            RestDecisionNN(PLAYER_STATE_SIZE + 1, HIDDEN_SIZE),
        )
        for _ in range(POP_SIZE)
    ]

    # create models/ dir for storing training models
    if not os.path.exists("teams/team_2/models"):
        os.makedirs("teams/team_2/models")

    print(
        f"""Training with:
 Population: {POP_SIZE} 
Generations: {MAX_GENERATIONS}
      Turns: {TURNS}
  Civilians: {CIVILIANS}\n"""
    )

    for generation in range(MAX_GENERATIONS):
        # Evaluate fitness

        fitness_scores = []
        with multiprocessing.Pool(multiprocessing.cpu_count()) as pool:
            worker_func = partial(evaluate_fitness, turns=TURNS, civilians=CIVILIANS)
            fitness_scores = pool.starmap(worker_func, population)

        avg_scores.append(np.mean(fitness_scores))
        max_scores.append(max(fitness_scores))

        # sort the population list based off the fitness_scores
        spop = [
            x
            for _, x in sorted(
                zip(fitness_scores, population), key=lambda p: p[0], reverse=True
            )
        ]
        # save the current best population
        signal.signal(signal.SIGINT, handle_signal(spop[0]))

        elitism_proportion = 0.2  # Adjust this proportion as needed
        elitism_count = max(1, int(elitism_proportion * len(population)))

        # Select parents based on fitness
        parents = select_parents(population, fitness_scores)

        # Retain top individuals as elites
        elites = parents[:elitism_count]

        # Generate offspring
        offspring = []
        # for now, only create offspring from TaskScorerNN
        for _ in range((len(population) - elitism_count) // 2):
            parent1, parent2 = random.sample(parents, 2)
            child_task = crossover(parent1[0], parent2[0], is_task=True)
            child_rest = crossover(parent1[1], parent2[1], is_task=False)
            mutate(child_task, 0.2, 0.05)
            mutate(child_rest, 0.2, 0.05)
            offspring.append((child_task, child_rest))

            parent1, parent2 = random.sample(parents, 2)
            child_task = crossover(parent1[0], parent2[0], is_task=True)
            child_rest = crossover(parent1[1], parent2[1], is_task=False)
            mutate(child_task, 0.2, 0.05)
            mutate(child_rest, 0.2, 0.05)
            offspring.append((child_task, child_rest))

        # Replace population
        [
            (mutate(ptask, 0.1, 0.02), mutate(prest, 0.1, 0.02))
            for ptask, prest in parents[1:]
        ]
        population = elites + offspring

        plot(avg_scores, max_scores)
        print(
            f"{generation + 1}/{MAX_GENERATIONS}: fitness scores: {sorted(fitness_scores, reverse=True)[:3]}"
        )

    best_model = select_parents(population, fitness_scores)[0]

    torch.save(
        best_model[0].state_dict(),
        f"task_weights.pth",
    )
    torch.save(
        best_model[1].state_dict(),
        f"rest_weights.pth",
    )
    print(
        'best model weights saved in "best_task_weights.pth" and "best_rest_weights.pth"'
    )
