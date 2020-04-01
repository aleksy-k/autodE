import numpy as np
from copy import deepcopy
from scipy.spatial import distance_matrix
from scipy.spatial.distance import cdist
from autode.log import logger


def length(vec):
    """Return the length of a vector"""
    return np.linalg.norm(vec)


def get_shifted_atoms_linear_interp(atoms, bonds, final_distances):
    """For a geometry defined by a set of xyzs, set the constrained bonds to the correct lengths

    Arguments:
        atoms (list(autode.atoms.Atom)): list of atoms
        bonds (list(tuple)): List of bond ids on for which the final_distances apply
        final_distances (list(float)): List of final bond distances for the bonds

    Returns:
        list(list): shifted xyzs
    """

    coords = np.array([atom.coord for atom in atoms])
    atoms_and_shift_vecs = {}

    for n, bond in enumerate(bonds):
        atom_a, atom_b = bond
        ab_vec = coords[atom_b] - coords[atom_a]
        ab_dist = np.linalg.norm(ab_vec)
        ab_final_dist = final_distances[n]

        ab_norm_vec = ab_vec / ab_dist

        atoms_and_shift_vecs[atom_b] = 0.5 * (ab_final_dist - ab_dist) * ab_norm_vec
        atoms_and_shift_vecs[atom_a] = -0.5 * (ab_final_dist - ab_dist) * ab_norm_vec

    for n, coord in enumerate(coords):
        if n in atoms_and_shift_vecs.keys():
            coord += atoms_and_shift_vecs[n]

        atoms[n].coord = coord

    return atoms


def get_rot_mat_kabsch(p_matrix, q_matrix):
    """
    Get the optimal rotation matrix with the Kabsch algorithm. Notation is from
    https://en.wikipedia.org/wiki/Kabsch_algorithm

    :param p_matrix: (np.ndarray)
    :param q_matrix: (np.ndarray)
    :return: (np.ndarray) rotation matrix
    """

    h = np.matmul(p_matrix.transpose(), q_matrix)
    u, s, vh = np.linalg.svd(h)
    d = np.linalg.det(np.matmul(vh.transpose(), u.transpose()))
    int_mat = np.identity(3)
    int_mat[2, 2] = d
    rot_matrix = np.matmul(np.matmul(vh.transpose(), int_mat), u.transpose())

    return rot_matrix


def get_krot_p_q(template_coords, coords_to_fit):
    """Get the optimum rotation matrix and pre & post translations """
    # Construct the P matrix in the Kabsch algorithm
    p_mat = deepcopy(coords_to_fit)
    p_centroid = np.average(p_mat, axis=0)
    p_mat_trans = get_centered_matrix(p_mat)

    # Construct the P matrix in the Kabsch algorithm
    q_mat = deepcopy(template_coords)
    q_centroid = np.average(q_mat, axis=0)
    q_mat_trans = get_centered_matrix(q_mat)

    # Get the optimum rotation matrix
    rot_mat = get_rot_mat_kabsch(p_mat_trans, q_mat_trans)

    # Apply to get the new set of coordinates
    # new_coords = np.array([np.matmul(rot_mat, coord - p_centroid) + q_centroid
    #                              for coord in coords])

    return rot_mat, p_centroid, q_centroid


def get_centered_matrix(mat):
    """For a list of coordinates n.e. a n_atoms x 3 matrix as a np array translate to the center of the coordinates"""
    centroid = np.average(mat, axis=0)
    return np.array([coord - centroid for coord in mat])


def get_neighbour_list(species, atom_i):
    """Calculate a neighbour list from atom i as a list of atom labels

    Arguments:
        atom_i (int): index of the atom
        species (autode.species.Species):

    Returns:
        list: list of atom ids in ascending distance away from atom_i
    """
    coords = species.get_coordinates()
    distance_vector = cdist(np.array([coords[atom_i]]), coords)[0]

    dists_and_atom_labels = {}
    for atom_j, dist in enumerate(distance_vector):
        dists_and_atom_labels[dist] = species.atoms[atom_j].label

    atom_label_neighbour_list = []
    for dist, atom_label in sorted(dists_and_atom_labels.items()):
        atom_label_neighbour_list.append(atom_label)

    return atom_label_neighbour_list


def get_distance_constraints(species):
    """Set all the distance constraints required in an optimisation as the active bonds"""
    distance_constraints = {}

    if species.graph is None:
        logger.warning('Molecular graph was not set cannot find any distance constraints')
        return None

    # Add the active edges(/bonds) in the molecular graph to the dict, value being the current distance
    for edge in species.graph.edges:

        if species.graph.edges[edge]['active']:
            distance_constraints[edge] = species.get_distance(*edge)

    return distance_constraints
