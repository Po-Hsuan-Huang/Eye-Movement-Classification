import cPickle as pickle
#Stores all the variables
IP_MAT_FileName = 'E_FVIEW_for_ONDRICTRLx_2016-09-13_13h37m45s_firstvisit.mat'
Actual_Res = {'height': 1024, 'width': 1280}
Saliency_Map_Res = {'height': 64, 'width': 80}
Saliency_Map_BaseDir = '/Users/jaypriyadarshi/Desktop/Jay/Eye-Movement-Classification/Feature_map'
Map_Types = ['C', 'F', 'I', 'M', 'O']
Saliency_Map_Receptive_Field = {'height': 8, 'width': 8}
max_saliency_SaveFile = 'max_saliency_vals.p'
Groups = [1,5]

#hyperparameters
hidden_size = 100 # size of hidden layer of neurons
seq_length = 15 # number of steps to unroll the RNN for
learning_rate = 1e-1

#model params
model_SaveFile = 'model.p'
