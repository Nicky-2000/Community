import itertools

global strong_players 
global remaining

strong_players = set()

def phaseIpreferences(player, community, global_random):
    global strong_players
    '''Return a list of task index and the partner id for the particular player. The output format should be a list of lists such that each element
    in the list has the first index task [index in the community.tasks list] and the second index as the partner id'''

    all_players = set(range(len(community.members)))
    
    for p in community.members:
        # assume the player can do all tasks perfectly until proven otherwise
        is_strong_player = True
        for t in community.tasks:
            # check if the player can perform the task perfectly
            if not all(p.abilities[i] >= t[i] for i in range(len(t))):
                is_strong_player = False
                break
        if is_strong_player:
            strong_players.add(p.id)

    # Form all possible partnerships from the remaining players
    remaining_players = all_players - strong_players
    partnerships = list(itertools.combinations(remaining_players, 2))
    partner_choices = []

    # Find good partnerships for the particular player
    for p1_id, p2_id in partnerships:
        if player.id == p1_id or player.id == p2_id:
            p1, p2 = community.members[p1_id], community.members[p2_id]
            joint_abilities = [max(a1, a2) for a1, a2 in zip(p1.abilities, p2.abilities)]
            for task_id in range(len(community.tasks)):
                # check if the partnership has greater ability than the task in all dimensions
                if all(joint_abilities[i] >= community.tasks[task_id][i] for i in range(len(t))):
                    partner_choices.append([task_id, p2_id]) if player.id == p1_id else partner_choices.append([task_id, p1_id])
    
    # Get the partnership bid by partnering with the weakest partner
    # sorted_partner_choices = sorted(
    #     partner_choices,
    #     key=lambda x: sum(community.members[x[1]].abilities)
    # )
    
    # remaining_players -= set([sorted_partner_choices[0][0], sorted_partner_choices[0][1]])

    # return [[sorted_partner_choices[0][2], sorted_partner_choices[0][1]]]
    
    return partner_choices

def phaseIIpreferences(player, community, global_random):
    '''Return a list of tasks for the particular player to do individually'''
    global strong_players 
    bids = []

    # If a player is strong, bid for all tasks as they can perform all
    if player.id in strong_players:
        for task_id, task in enumerate(community.tasks):
            bids.append(task_id)
        return bids

    # Assign remaining tasks as long as energy loss is 0
    if player.energy < 0:
        return bids
    
    num_abilities = len(player.abilities)

    for task_id, task in enumerate(community.tasks):
        energy_cost = sum([max(task[j] - player.abilities[j], 0) for j in range(num_abilities)])
        if energy_cost <= 2 or (energy_cost <= 4 and player.energy >= 8):
            bids.append(task_id)
    
    return bids