from community import Community, Member
from teams.team_10.constants import * 
import pandas as pd
import numpy as np
from typing import List 

def phaseIpreferences(player: Member, community: Community, global_random):
    '''Return a list of task index and the partner id for the particular player. The output format should be a list of lists such that each element
    in the list has the first index task [index in the community.tasks list] and the second index as the partner id'''
    acceptable_energy = get_acceptable_energy_level(num_of_tasks=len(community.tasks), p=len(community.members))
    # solo = solo_tasks(player, community.tasks, acceptable_energy)
    pairs = find_pairs(player, community.tasks, community.members, acceptable_energy)
    return pairs
    

def phaseIIpreferences(player: Member, community: Community, global_random):
    '''Return a list of tasks for the particular player to do individually'''
    SACRIFICE_TIME = len(community.members) // 2
    sacrifices = sacrifice(community.members, community.tasks)

    if len(community.tasks) < SACRIFICE_TIME and sacrifices:
        to_be_sacrificed = find_weakest_agents(community.members, len(sacrifices))
        if player.id in to_be_sacrificed: 
            return sacrifices 
        
    acceptable_energy = get_acceptable_energy_level(num_of_tasks=len(community.tasks), p=len(community.members))
    solo = solo_tasks(player, community.tasks, acceptable_energy)
    return solo

"""
get_acceptable_energy_level (num_of_tasks, p)
- returns the energy level to which a member's energy can drop to based on how many tasks are left to do. 
"""
def get_acceptable_energy_level(num_of_tasks: int, p: int) -> int:
    acceptable_energy = NORMAL_ENERGY_LEVEL
    if num_of_tasks < 9 * p / 10:
        acceptable_energy -= 1
    elif num_of_tasks < 8 * p / 10:
        acceptable_energy -= 2
    elif num_of_tasks < 7 * p / 10:
        acceptable_energy -= 3
    elif num_of_tasks < 6 * p / 10:
        acceptable_energy -= 4
    elif num_of_tasks < 5 * p / 10:
        acceptable_energy -= 5
    elif num_of_tasks < 4 * p / 10:
        acceptable_energy -= 6
    elif num_of_tasks < 3 * p / 10:
        acceptable_energy -= 7
    elif num_of_tasks < 2 * p / 10:
        acceptable_energy -= 8
    elif num_of_tasks < 1 * p / 10:
        acceptable_energy -= 9
    return acceptable_energy

def solo_tasks(player: Member, tasks, acceptable_energy_level) -> dict[int, int]:
    alone_tasks = {} # task: resulting energy
    our_abilities_np = np.array(player.abilities)

    for task_id, task in enumerate(tasks):
        task_np = np.array(task)
        diff = our_abilities_np - task_np
        negative_sum = np.sum(diff[diff < 0])

        if player.energy + negative_sum > acceptable_energy_level:
            alone_tasks[task_id] = player.energy + negative_sum 

    return alone_tasks

def find_pairs(player: Member, tasks, members, acceptable_energy_level) -> list[int]:
    # [Task_ID, other_player_id]
    task_player_pairs = []
    our_abilities_np = np.array(player.abilities)
    our_id = player.id
    for task_id, task in enumerate(tasks):
        task_np = np.array(task)

        for other_person in members:
            if other_person.id == our_id:
                continue

            others_abilities_np = np.array(other_person.abilities)
            combined_abilties = np.maximum(our_abilities_np, others_abilities_np)

            diff = combined_abilties - task_np
            negative_sum = np.sum(diff[diff < 0])
            player_above_acceptable_energy = (
                player.energy + negative_sum > acceptable_energy_level
            )
            other_person_above_acceptable_energy = (
                other_person.energy + negative_sum > acceptable_energy_level
            )
            if player_above_acceptable_energy and other_person_above_acceptable_energy:
                task_player_pairs.append((abs(negative_sum), [task_id, other_person.id]))
    
    least_energy_pairs = sorted(task_player_pairs)
    pairs = []
    for i in range(8):
        if len(least_energy_pairs) <= i - 1:
            break
        print (least_energy_pairs[i][1])
        pairs.append(least_energy_pairs[i][1])

    return pairs

def find_weakest_agents(members: List[Member], n: int) -> list[int]:
    """Return the id of the weakest agents in the community"""
    agents = [(member.id, sum(member.abilities)) for member in members if not member.incapacitated]

    three_weakest_agents = sorted(agents, key=lambda x: x[1])[:n]
    weakest_agent_ids = [agent[0] for agent in three_weakest_agents]
    return weakest_agent_ids

"""
sacrifice(members, tasks)
- identifies if there are tasks that require sacrificing members
- returns a list of tasks that require sacrifices
"""
def sacrifice(members: List[Member], tasks: List) -> List[int]:
    exhausting_tasks = []
    for i in range(len(tasks)):
        task = tasks[i]
        task_np = np.array(task)
        not_exhausting = False
        for member in members:
            abilities_np = np.array(member.abilities)
            diff = abilities_np - task_np
            # if one member can complete it themselves without being sacrificed
            if np.sum(diff[diff < 0]) < (MAX_ENERGY_LEVEL - EXHAUSTED_ENERGY_LEVEL):
                not_exhausting = True
            # else, check pairs 
            else:
                for other in members:
                    other_np = np.array(other.abilities)
                    combined_np = np.maximum(abilities_np, other_np)
                    diff = combined_np - task_np
                    if np.sum(diff[diff < 0]) < (MAX_ENERGY_LEVEL - EXHAUSTED_ENERGY_LEVEL) * 2:
                        not_exhausting = True
                        break
            if not_exhausting:
                break
        if not not_exhausting:
            exhausting_tasks.append(i)
    return exhausting_tasks
