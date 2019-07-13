from .config import Config
from .log import logger
from .geom import get_breaking_bond_atom_id_dist_dict
from .pes_1d import get_orca_ts_guess_1dpes_scan
from .pes_1d import get_xtb_ts_guess_1dpes_scan
from .pes_2d import get_orca_ts_guess_2d
from .geom import get_valid_mappings_frags_to_whole_graph
from .template_ts_guess import get_template_ts_guess
from .optts import get_ts
from .reactions import Dissociation


def find_ts(reaction):
    """
    Find a transition state for a dissociative reaction i.e. reactant1 -> product1 + product2
    :param reaction:
    :return:
    """
    logger.info('Finding TS for a dissociation reaction')
    reactant = reaction.reacs[0]
    bbond_ids = find_breaking_bond_ids(reaction)

    transition_state = find_ts_breaking_bond(reactant, bbond_ids)

    if transition_state is None:
        logger.error('Could not find a suitable transition state')

    return transition_state


def find_ts_breaking_bond(reactant, bbonds, fbonds=None):
    """
    Find the TS where bond(s) are broken
    :param reactant: (object) reactant object
    :param bbonds: (list(tuple)) list of n elements where n is the number of broken bonds containing a tuple of the
    atom ids
    :param fbonds: (list(tuple)) as above for forming bonds. Here as this function is called from substitution
    where a 1D scan is sufficient to find the TS
    :return:
    """

    bbond_atom_ids_and_dists = get_breaking_bond_atom_id_dist_dict(reactant.xyzs, bbonds)

    for ts_guess_func in get_ts_guess_functions(bbonds):
        logger.info('Guessing at a TS geometry')
        ts_guess = ts_guess_func(reactant, bbond_atom_ids_and_dists, fbonds)

        if ts_guess.xyzs is not None:
            logger.info('Found a TS guess geometry with ' + ts_guess_func.__name__)
            ts_guess.name = ts_guess_func.__name__ + '_TS'

            if fbonds is not None:
                logger.info('Adding forming bonds to the list of active bonds in the TS')
                ts_guess.active_bonds += fbonds

            transition_state = get_ts(ts_guess)
            if transition_state is not None:
                return transition_state
    return None


def find_breaking_bond_ids(reaction):
    """
    Given a reaction object find the bonds that are broken going from the reactant to *two* products
    :param reaction:
    :return: (list(tuple)) list of breaking bonds
    """
    logger.info('Finding breaking bond(s) for a dissociation reaction')

    reactant, prod1, prod2 = reaction.reacs[0], reaction.prods[0], reaction.prods[1]

    valid_mappings = get_valid_mappings_frags_to_whole_graph(whole_graph=reactant.graph, frag1_graph=prod1.graph,
                                                             frag2_graph=prod2.graph)
    bbond_atom_ids_list = get_breaking_bond_ids(reactant.graph, valid_mappings)
    logger.info('Found *{}* breaking bonds'.format(len(bbond_atom_ids_list)))

    return bbond_atom_ids_list


def get_template_ts_guess_breaking_bonds(reactant, bbonds_and_dists, fbonds=None):
    active_bonds = list(bbonds_and_dists.keys()) if fbonds is None else list(bbonds_and_dists.keys()) + fbonds
    return get_template_ts_guess(mol=reactant, active_bonds=active_bonds, reaction_class=Dissociation)


def get_orca_ts_guess_coarse(reactant, bbonds_and_dists, fbonds=None):
    logger.info('Running a coarse PES scan with keywords set in Config')
    atom_ids, dist = list(bbonds_and_dists.items())[0]
    return get_orca_ts_guess_1dpes_scan(reactant, atom_ids, dist, final_dist=dist+1.5,  n_steps=10,
                                        orca_keywords=Config.scan_keywords, name='default', reaction_class=Dissociation)


def get_orca_ts_guess_coarse_alt(reactant, bbonds_and_dists, fbonds=None):
    logger.info('Running a coarse PES scan at PBE0-D3BJ/de2-SVP')
    kws = ['Opt', 'PBE0', 'RIJCOSX', 'D3BJ', 'def2-SVP', 'def2/J']
    atom_ids, dist = list(bbonds_and_dists.items())[0]
    return get_orca_ts_guess_1dpes_scan(reactant, atom_ids, dist, final_dist=dist+1.5, n_steps=10,
                                        orca_keywords=kws, name='alt', reaction_class=Dissociation)


def get_xtb_ts_guess_breaking_bond(reactant, bbonds_and_dists, fbonds=None):
    atom_ids, dist = list(bbonds_and_dists.items())[0]
    return get_xtb_ts_guess_1dpes_scan(reactant, atom_ids, dist, final_dist=dist+1.5, n_steps=20,
                                       reaction_class=Dissociation)


def get_orca_ts_guess_2d_breaking_bonds(mol, bbonds_and_dists, fbonds=None, reaction_class=Dissociation, name='2d',
                                        max_bond_dist_add=1.5, n_steps=7, orca_keywords=Config.scan_keywords):
    """
    Get a TS guess from a 2d orca scan when two bonds are broken
    :param mol: molecule object
    :param bbonds_and_dists: (dict) tuples of breaking bond atom ids and floats of current distance
    :param reaction_class: class of the reaction (reactions.py)
    :param max_bond_dist_add: (float) maximum distance to add in the breaking (Å)
    :param n_steps: (int) number of scan steps to perform in each dimenesion for n_steps^2 total number
    :param name: (str) name of the TS
    :param orca_keywords: (list) list of ORCA keywords to use in the calculation
    :return:
    """

    bond_ids, curr_bond_dists = list(bbonds_and_dists.keys()), list(bbonds_and_dists.values())
    curr_dist1, curr_dist2 = curr_bond_dists[0], curr_bond_dists[1]
    final_dist1, final_dist2 = curr_bond_dists[0] + max_bond_dist_add, curr_bond_dists[1] + max_bond_dist_add

    return get_orca_ts_guess_2d(mol, bond_ids, curr_dist1, final_dist1, curr_dist2, final_dist2, reaction_class,
                                n_steps, name, orca_keywords)


def get_breaking_bond_ids(reactant_graph, valid_mappings):
    """
    For a list of valid mappings determine the breaking bonds (returned as a list of tuples, which are atoms ids
    defining the bond) these will have inter-fragment bonds..

    :param reactant_graph: networkX graph
    :param valid_mappings: (list(tuple(dict))) List of valid mappings
    :return:
    """

    breaking_bond_atom_ids_list = []
    for mapping_pair in valid_mappings:
        for frag1_atom_id in mapping_pair[0].keys():
            for frag2_atom_id in mapping_pair[1].keys():
                atom_ij = frag1_atom_id, frag2_atom_id
                if reactant_graph.has_edge(*atom_ij) and atom_ij not in breaking_bond_atom_ids_list:
                    breaking_bond_atom_ids_list.append(atom_ij)

    return breaking_bond_atom_ids_list


def get_ts_guess_functions(bbond_ids):
    """
    Get functions that will find TS guesses given the number of breaking bonds in the TS
    :param bbond_ids:
    :return:
    """

    if len(bbond_ids) == 1:
        return [get_template_ts_guess_breaking_bonds, get_orca_ts_guess_coarse, get_orca_ts_guess_coarse_alt]
        # return [get_orca_ts_guess_coarse, get_orca_ts_guess_coarse_alt]
        # also have the nor very good: get_xtb_ts_guess_breaking_bond
    elif len(bbond_ids) == 2:
        return [get_template_ts_guess_breaking_bonds, get_orca_ts_guess_2d_breaking_bonds]
        # also have the nor very good: get_xtb_ts_guess_2d
    else:
        logger.critical('Can\'t yet handle >2 or 0 bonds changing')
        exit()