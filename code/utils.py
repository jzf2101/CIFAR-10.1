import io
import json
import os
import pickle

import numpy as np
import pandas as pd
import scipy.stats
import pathlib
import PIL.Image
import cifar10

cifar10_label_names = ['airplane', 'automobile', 'bird', 'cat', 'deer', 'dog', 'frog', 'horse', 'ship', 'truck']


def np_to_png(a, fmt='png', scale=1):
    a = np.uint8(a)
    f = io.BytesIO()
    tmp_img = PIL.Image.fromarray(a)
    tmp_img = tmp_img.resize((scale * 32, scale * 32), PIL.Image.NEAREST)
    tmp_img.save(f, fmt)
    return f.getvalue()


def load_new_test_data(version_string='', load_tinyimage_indices=False):
    data_path = os.path.join(os.path.dirname(__file__), '../datasets/')
    filename = 'cifar10.1'
    if version_string == '':
        version_string = 'v7'
    if version_string in ['v4', 'v6', 'v7']:
        filename += '_' + version_string
    else:
        raise ValueError('Unknown dataset version "{}".'.format(version_string))
    label_filename = filename + '_labels.npy'
    imagedata_filename = filename + '_data.npy'
    label_filepath = os.path.abspath(os.path.join(data_path, label_filename))
    imagedata_filepath = os.path.abspath(os.path.join(data_path, imagedata_filename))
    print('Loading labels from file {}'.format(label_filepath))
    assert pathlib.Path(label_filepath).is_file()
    labels = np.load(label_filepath)
    print('Loading image data from file {}'.format(imagedata_filepath))
    assert pathlib.Path(imagedata_filepath).is_file()
    imagedata = np.load(imagedata_filepath)
    assert len(labels.shape) == 1
    assert len(imagedata.shape) == 4
    assert labels.shape[0] == imagedata.shape[0]
    assert imagedata.shape[1] == 32
    assert imagedata.shape[2] == 32
    assert imagedata.shape[3] == 3
    if version_string == 'v6' or version_string == 'v7':
        assert labels.shape[0] == 2000
    elif version_string == 'v4':
        assert labels.shape[0] == 2021

    if not load_tinyimage_indices:
        return imagedata, labels
    else:
        ti_indices_data_path = os.path.join(os.path.dirname(__file__), '../other_data/')
        ti_indices_filename = 'cifar10.1_' + version_string + '_ti_indices.json'
        ti_indices_filepath = os.path.abspath(os.path.join(ti_indices_data_path, ti_indices_filename))
        print('Loading Tiny Image indices from file {}'.format(ti_indices_filepath))
        assert pathlib.Path(ti_indices_filepath).is_file()
        with open(ti_indices_filepath, 'r') as f:
            tinyimage_indices = json.load(f)
        assert type(tinyimage_indices) is list
        assert len(tinyimage_indices) == labels.shape[0]
        return imagedata, labels, tinyimage_indices


def load_distances_to_cifar10(version_string=''):
    data_path = os.path.join(os.path.dirname(__file__), '../other_data/')
    filename = 'tinyimage_cifar10_distances'
    if version_string != '':
        filename += '_' + version_string
    filename += '.json'
    filepath = os.path.abspath(os.path.join(data_path, filename))
    print('Loading distances from file {}'.format(filepath))
    assert pathlib.Path(filepath).is_file()
    with open(filepath, 'r') as f:
        tmp = json.load(f)
    if version_string == 'v4':
        assert len(tmp) == 372131
    elif version_string == 'v6':
        assert len(tmp) == 1646248
    elif version_string == 'v7':
        assert len(tmp) == 589711
    result = {}
    for k, v in tmp.items():
        result[int(k)] = v
    return result


def load_tinyimage_subset(version_string=''):
    other_data_path = os.path.join(os.path.dirname(__file__), '../other_data/')
    image_data_filename = 'tinyimage_subset_data'
    if version_string != '':
        image_data_filename += '_' + version_string
    image_data_filename += '.pickle'
    image_data_filepath = os.path.abspath(os.path.join(other_data_path, image_data_filename))
    indices_filename = 'tinyimage_subset_indices'
    if version_string != '':
        indices_filename += '_' + version_string
    indices_filename += '.json'
    indices_filepath = os.path.abspath(os.path.join(other_data_path, indices_filename))
    print('Loading indices from file {}'.format(indices_filepath))
    assert pathlib.Path(indices_filepath).is_file()
    print('Loading image data from file {}'.format(image_data_filepath))
    assert pathlib.Path(image_data_filepath).is_file()
    with open(indices_filepath, 'r') as f:
        indices = json.load(f)
    with open(image_data_filepath, 'rb') as f:
        image_data = pickle.load(f)
    num_entries = 0
    for kw, kw_indices in indices.items():
        for entry in kw_indices:
            assert entry['tinyimage_index'] in image_data
            num_entries += 1
    assert num_entries == len(image_data)
    return indices, image_data


def load_cifar10_by_keyword(unique_keywords=True, version_string=''):
    cifar10_keywords = load_cifar10_keywords(unique_keywords=unique_keywords,
                                             lists_for_unique=True,
                                             version_string=version_string)
    cifar10_by_keyword = {}
    for ii, keyword_entries in enumerate(cifar10_keywords):
        for entry in keyword_entries:
            cur_keyword = entry['nn_keyword']
            if not cur_keyword in cifar10_by_keyword:
                cifar10_by_keyword[cur_keyword] = []
            cifar10_by_keyword[cur_keyword].append(ii)
    return cifar10_by_keyword


def load_cifar10_keywords(unique_keywords=True, lists_for_unique=False, version_string=''):
    other_data_path = os.path.join(os.path.dirname(__file__), '../other_data/')
    filename = 'cifar10_keywords'
    if unique_keywords:
        filename += '_unique'
    if version_string != '':
        filename += '_' + version_string
    filename += '.json'
    keywords_filepath = os.path.abspath(os.path.join(other_data_path, filename))
    print('Loading keywords from file {}'.format(keywords_filepath))
    assert pathlib.Path(keywords_filepath).is_file()
    with open(keywords_filepath, 'r') as f:
        cifar10_keywords = json.load(f)
    if unique_keywords and lists_for_unique:
        result = []
        for entry in cifar10_keywords:
            result.append([entry])
    else:
        result = cifar10_keywords
    assert len(result) == 60000
    return result


def compute_accuracy(pred, labels):
    return np.sum(pred == labels) / float(len(labels))


def clopper_pearson(k,n,alpha=0.05):
    """
    http://en.wikipedia.org/wiki/Binomial_proportion_confidence_interval
    alpha confidence intervals for a binomial distribution of k expected successes on n trials
    Clopper Pearson intervals are a conservative estimate.
    """
    lo = scipy.stats.beta.ppf(alpha/2, k, n-k+1)
    hi = scipy.stats.beta.ppf(1 - alpha/2, k+1, n-k)
    return lo, hi


def get_model_names():
    model_names = []
    suffix = '_predictions.json'
    original_predictions_path = os.path.join(os.path.dirname(__file__), 
                                        '../model_predictions/original_predictions')
    for p in pathlib.Path(original_predictions_path).glob('*.json'):
        assert str(p).endswith(suffix)
        cur_name = str(p.name)[:-(len(suffix))]
        model_names.append(cur_name)
    model_names = sorted(model_names)
    return model_names


def get_original_predictions():
    # Load original predictions
    original_predictions = {}
    suffix = '_predictions.json'
    original_predictions_path = os.path.join(os.path.dirname(__file__), 
                                       '../model_predictions/original_predictions')
    for p in pathlib.Path(original_predictions_path).glob('*.json'):
        assert str(p).endswith(suffix)
        cur_name = str(p.name)[:-(len(suffix))]
        with open(p, 'r') as f:
            original_predictions[cur_name] = np.array(json.load(f))
    return original_predictions


def get_new_predictions(version):
    new_predictions = {}
    suffix = '_predictions.json'
    new_predictions_path = os.path.join(os.path.dirname(__file__), 
                                        '../model_predictions/v{}_predictions'.format(version))
    for p in pathlib.Path(new_predictions_path).glob('*.json'):
        assert str(p).endswith(suffix)
        cur_name = str(p.name)[:-(len(suffix))]
        with open(p, 'r') as f:
            new_predictions[cur_name] = np.array(json.load(f))
    return new_predictions 


def get_prediction_dataframe(version):
    '''Returns a pandas dataframe containing model accuracies, error, and gap.'''
    
    # Get the original and new true labels
    cifar_filepath = os.path.join(os.path.dirname(__file__), '../other_data/cifar10')
    cifar = cifar10.CIFAR10Data(cifar_filepath)
    original_test_labels = cifar.eval_labels
    _, new_true_labels = load_new_test_data(version)
    
    # Get the model predictions
    model_names = get_model_names()
    new_predictions = get_new_predictions(version)
    original_predictions = get_original_predictions()

    pd_data = {}
    for m in model_names:
        cur_dict = {}
        pd_data[m] = cur_dict
        cur_dict['New Acc.'] = 100 * compute_accuracy(new_predictions[m], new_true_labels)
        cur_dict['Original Acc.'] = 100 * compute_accuracy(original_predictions[m], original_test_labels)
        cur_dict['Gap'] = cur_dict['Original Acc.'] - cur_dict['New Acc.']
        cur_dict['Original Err.'] = 100 - cur_dict['Original Acc.']
        cur_dict['New Err.'] = 100 - cur_dict['New Acc.']
        cur_dict['Error Ratio'] = cur_dict['New Err.'] / cur_dict['Original Err.']
        cur_dict['New CI'] = clopper_pearson(np.sum(new_predictions[m] == new_true_labels), len(new_true_labels))
        cur_dict['Original CI'] = clopper_pearson(np.sum(original_predictions[m] == original_test_labels), 10000)

    df= pd.DataFrame(pd_data).transpose()[['Original Acc.', 'New Acc.', 'Gap', 
                                        'Original Err.', 'New Err.', 'Error Ratio']]
    return df


def compute_l2_distances(images, other_vec):
    tmp_images = images - other_vec
    dsts = np.linalg.norm(tmp_images, axis=1)
    assert len(dsts) == images.shape[0]
    return dsts


def find_near_self_duplicates(images, ind, low_threshold, high_threshold):
    dsts = compute_l2_distances(images, images[ind,:])
    n = len(dsts)
    result = []
    for ii in range(n):
        if ii != ind and low_threshold <= dsts[ii] and dsts[ii]<= high_threshold:
            result.append((ii, dsts[ii]))
    return result
