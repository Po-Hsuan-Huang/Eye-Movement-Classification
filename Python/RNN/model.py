import numpy as np
import vars

class Model(object):
    def __init__(self, hidden_size, num_classes, num_regions, seq_length):
        # model parameters
        self.hidden_size = hidden_size
        self.ip_dim = vars.ip_dim
        self.num_classes = num_classes
        self.num_regions = num_regions #number of regions after segmenting the saliency map
        self.seq_length = seq_length
        self.Wxh = np.random.randn(hidden_size, self.ip_dim)*0.01 # input to hidden
        self.Whh1 = np.random.randn(hidden_size, hidden_size)*0.01 # hidden to hidden
        self.Whh2 = np.random.randn(hidden_size, hidden_size)*0.01 # hidden to hidden - 2nd RNN layer
        self.Wh1h2 = np.random.randn(hidden_size, hidden_size)*0.01 # hidden to hidden - b/w 1st and 2nd RNN layer
        self.Why1 = np.random.randn(num_classes, hidden_size)*0.01 # hidden to output1 - ALS, PARK, CTRL, etc. participant label
        self.Why2 = np.random.randn(num_regions, hidden_size)*0.01 # hidden to output2 - location
        self.bh1 = np.zeros((hidden_size, 1)) # hidden1 bias
        self.bh2 = np.zeros((hidden_size, 1)) # hidden2 bias
        self.by1 = np.zeros((num_classes, 1)) # output1 bias
        self.by2 = np.zeros((num_regions, 1)) # output2 bias
        self.smooth_loss = -np.log(1.0/self.num_classes)*seq_length + -np.log(1.0/self.num_regions)*seq_length # loss at iteration 0

    def forward_pass(self, inputs, grp_targets, loc_targets, hprev1, hprev2, avg_saliency_region):
        xs, hs1, hs2, ys1, ys2, ps1, ps2 = {}, {}, {}, {}, {}, {}, {}
        hs1[-1] = np.copy(hprev1)
        hs2[-1] = np.copy(hprev2) 
        loss = 0
        inputs = map(lambda (l,s): 
            [l, s[0] + self.num_regions, s[1] + self.num_regions + vars.n_bins, s[2] + self.num_regions + (2 * vars.n_bins), s[3] + self.num_regions + (3 * vars.n_bins), s[4] + self.num_regions + (4 * vars.n_bins)], inputs)
        for t in xrange(len(inputs)):
            xs[t] = np.zeros((self.num_regions + (len(vars.Map_Types) * vars.n_bins),1)) # create a sparse vector
            #print inputs[t]
            xs[t][inputs[t]] = 1
            #print "Wxh size: ", self.Wxh.shape
            #print "input size: ", xs[t].shape
            #print "avg size: ", avg_saliency_region[t].shape
            xs[t] = np.vstack((xs[t], avg_saliency_region[t].reshape(avg_saliency_region[t].shape[0], 1)))
            hs1[t] = np.tanh(np.dot(self.Wxh, xs[t]) + np.dot(self.Whh1, hs1[t-1]) + self.bh1) # hidden state 1
            ys1[t] = np.dot(self.Why1, hs1[t]) + self.by1 # unnormalized log probabilities for participant group
            ps1[t] = np.exp(ys1[t]) / np.sum(np.exp(ys1[t])) # probabilities for participant group
            hs2[t] = np.tanh(np.dot(self.Wh1h2, hs1[t]) + np.dot(self.Whh2, hs2[t-1]) + self.bh2) # hidden state 2
            ys2[t] = np.dot(self.Why2, hs2[t]) + self.by2 # unnormalized log probabilities for next location
            ps2[t] = np.exp(ys2[t]) / np.sum(np.exp(ys2[t])) # probabilities for next location
            #print 't: ', t
            #print 'grp_targets: ', grp_targets[t]
            #print 'loc_targets: ', loc_targets[t]
            loss += -np.log(ps1[t][grp_targets[t],0]) + -np.log(ps2[t][loc_targets[t],0]) #1st and 2nd softmax (cross-entropy loss)
        return loss, xs, hs1, hs2, ps1, ps2, inputs


    def backward_pass(self, inputs, grp_targets, loc_targets, xs, hs1, hs2, ps1, ps2):
        dWxh, dWhh1, dWhh2, dWh1h2, dWhy1, dWhy2 = np.zeros_like(self.Wxh), np.zeros_like(self.Whh1), np.zeros_like(self.Whh2), np.zeros_like(self.Wh1h2), np.zeros_like(self.Why1), np.zeros_like(self.Why2)
        dbh1, dbh2, dby1, dby2 = np.zeros_like(self.bh1), np.zeros_like(self.bh2), np.zeros_like(self.by1), np.zeros_like(self.by2)
        dh1next = np.zeros_like(hs1[0])
        dh2next = np.zeros_like(hs2[0])
        for t in reversed(xrange(len(inputs))):
            dy2 = np.copy(ps2[t])
            dy2[loc_targets[t]] -= 1 # backprop into y2
            dWhy2 += np.dot(dy2, hs2[t].T)
            dby2 += dy2
            dh2 = np.dot(self.Why2.T, dy2) + dh2next # backprop into h2
            dhraw2 = (1 - hs2[t] * hs2[t]) * dh2 # backprop through tanh nonlinearity
            dbh2 += dhraw2
            dWh1h2 += np.dot(dhraw2, hs1[t].T)
            dWhh2 += np.dot(dhraw2, hs2[t-1].T)
            dh1 = np.dot(self.Wh1h2.T, dhraw2) #review
            dh2next = np.dot(self.Whh2.T, dhraw2)
            #backprop through layer-1 
            dy1 = np.copy(ps1[t])
            dy1[grp_targets[t]] -= 1 # backprop into y1
            dWhy1 += np.dot(dy1, hs1[t].T)
            dby1 += dy1
            dh1 += np.dot(self.Why1.T, dy1) + dh1next # backprop into h1
            dhraw1 = (1 - hs1[t] * hs1[t]) * dh1 # backprop through tanh nonlinearity
            dbh1 += dhraw1
            dWxh += np.dot(dhraw1, xs[t].T)
            dWhh1 = np.dot(dhraw1, hs1[t-1].T)
            dh1next = np.dot(self.Whh1.T, dhraw1) 
        return dWxh, dWhh1, dWhh2, dWh1h2, dWhy1, dWhy2, dbh1, dbh2, dby1, dby2

    def _loss(self, inputs, grp_targets, loc_targets, hprev1, hprev2, avg_saliency_region):
        """
        inputs,targets are both list of integers.
        hprev is Hx1 array of initial hidden state
        returns the loss, gradients on model parameters, and last hidden state
        """
        # forward pass
        loss, xs, hs1, hs2, ps1, ps2, inputs = self.forward_pass(inputs, grp_targets, loc_targets, hprev1, hprev2, avg_saliency_region)
        # backward pass: compute gradients going backwards
        dWxh, dWhh1, dWhh2, dWh1h2, dWhy1, dWhy2, dbh1, dbh2, dby1, dby2 = self.backward_pass(inputs, grp_targets, loc_targets, xs, hs1, hs2, ps1, ps2)
        for dparam in [dWxh, dWhh1, dWhh2, dWh1h2, dWhy1, dWhy2, dbh1, dbh2, dby1, dby2]:
            np.clip(dparam, -5, 5, out=dparam) # clip to mitigate exploding gradients
        return loss, dWxh, dWhh1, dWhh2, dWh1h2, dWhy1, dWhy2, dbh1, dbh2, dby1, dby2, hs1[len(grp_targets)-1], hs2[len(loc_targets)-1]

    def _predict(self, inputs, hs1, hs2, avg_saliency_region):
        inputs = map(lambda (l,s): 
            [l, s[0] + self.num_regions, s[1] + self.num_regions + vars.n_bins, s[2] + self.num_regions + (2 * vars.n_bins), s[3] + self.num_regions + (3 * vars.n_bins), s[4] + self.num_regions + (4 * vars.n_bins)], inputs)
        for t in xrange(len(inputs)):
            x = np.zeros((self.num_regions + (len(vars.Map_Types) * vars.n_bins),1)) # encode in 1-of-k representation
            x[inputs[t]] = 1
            x = np.vstack((x, avg_saliency_region[t].reshape(avg_saliency_region[t].shape[0], 1)))
            hs1 = np.tanh(np.dot(self.Wxh, x) + np.dot(self.Whh1, hs1) + self.bh1) # hidden state 1
            ys1 = np.dot(self.Why1, hs1) + self.by1 # unnormalized log probabilities for participant group
            ps1 = np.exp(ys1) / np.sum(np.exp(ys1)) # probabilities for participant group
            hs2 = np.tanh(np.dot(self.Wh1h2, hs1) + np.dot(self.Whh2, hs2) + self.bh2) # hidden state 2
            ys2 = np.dot(self.Why2, hs2) + self.by2 # unnormalized log probabilities for next location
            ps2 = np.exp(ys2) / np.sum(np.exp(ys2)) # probabilities for next location
        return np.argsort(ps1.ravel())[-1]
