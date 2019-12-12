# -*- coding: utf-8 -*-
"""
Created on Sat May 25 14:51:02 2019

@author: Suraj Pawar
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import norm 
from sklearn.preprocessing import MinMaxScaler
from numpy.random import seed
seed(1)
from tensorflow import set_random_seed
set_random_seed(2)
from sklearn.model_selection import train_test_split
from utils import *
import os
import time as tm
import csv

from sklearn.tree import DecisionTreeRegressor

font = {'family' : 'Times New Roman',
        'size'   : 14}	
plt.rc('font', **font)

#%%
#Class of problem to solve 2D decaying homogeneous isotrpic turbulence
class DHIT:
    def __init__(self,nx,ny,nxf,nyf,freq,n_snapshots,n_snapshots_train,n_snapshots_test,
                 istencil,ifeatures,ilabel):
        
        '''
        initialize the DHIT class
        
        Inputs
        ------
        n_snapshots : number of snapshots available
        nx,ny : dimension of the snapshot

        '''
        
        self.nx = nx
        self.ny = ny
        self.nxf = nxf
        self.nyf = nyf
        self.freq = freq
        self.n_snapshots = n_snapshots
        self.n_snapshots_train = n_snapshots_train
        self.n_snapshots_test = n_snapshots_test
        self.istencil = istencil
        self.ifeatures = ifeatures
        self.ilabel = ilabel
        
        self.uc = np.zeros(shape=(self.n_snapshots, self.nx+1, self.ny+1), dtype='double')
        self.vc = np.zeros(shape=(self.n_snapshots, self.nx+1, self.ny+1), dtype='double')
        self.ucx = np.zeros(shape=(self.n_snapshots, self.nx+1, self.ny+1), dtype='double')
        self.ucy = np.zeros(shape=(self.n_snapshots, self.nx+1, self.ny+1), dtype='double')
        self.vcx = np.zeros(shape=(self.n_snapshots, self.nx+1, self.ny+1), dtype='double')
        self.vcy = np.zeros(shape=(self.n_snapshots, self.nx+1, self.ny+1), dtype='double')
        self.ucxx = np.zeros(shape=(self.n_snapshots, self.nx+1, self.ny+1), dtype='double')
        self.ucyy = np.zeros(shape=(self.n_snapshots, self.nx+1, self.ny+1), dtype='double')
        self.vcxx = np.zeros(shape=(self.n_snapshots, self.nx+1, self.ny+1), dtype='double')
        self.vcyy = np.zeros(shape=(self.n_snapshots, self.nx+1, self.ny+1), dtype='double')
        self.t11 = np.zeros(shape=(self.n_snapshots, self.nx+1, self.ny+1), dtype='double')
        self.t12 = np.zeros(shape=(self.n_snapshots, self.nx+1, self.ny+1), dtype='double')
        self.t22 = np.zeros(shape=(self.n_snapshots, self.nx+1, self.ny+1), dtype='double')
        self.nu = np.zeros(shape=(self.n_snapshots, self.nx+1, self.ny+1), dtype='double')
        
        for m in range(1,self.n_snapshots+1):
            folder = "data_"+ str(self.nxf) + "_" + str(self.nx) 
            
            file_input = "../data_spectral/"+folder+"/uc/uc_"+str(m)+".csv"
            data_input = np.genfromtxt(file_input, delimiter=',')
            self.uc[m-1,:,:] = data_input
            
            file_input = "../data_spectral/"+folder+"/vc/vc_"+str(m)+".csv"
            data_input = np.genfromtxt(file_input, delimiter=',')
            self.vc[m-1,:,:] = data_input
            
            file_input = "../data_spectral/"+folder+"/ucx/ucx_"+str(m)+".csv"
            data_input = np.genfromtxt(file_input, delimiter=',')
            self.ucx[m-1,:,:] = data_input
            
            file_input = "../data_spectral/"+folder+"/ucy/ucy_"+str(m)+".csv"
            data_input = np.genfromtxt(file_input, delimiter=',')
            self.ucy[m-1,:,:] = data_input
            
            file_input = "../data_spectral/"+folder+"/vcx/vcx_"+str(m)+".csv"
            data_input = np.genfromtxt(file_input, delimiter=',')
            self.vcx[m-1,:,:] = data_input
            
            file_input = "../data_spectral/"+folder+"/vcy/vcy_"+str(m)+".csv"
            data_input = np.genfromtxt(file_input, delimiter=',')
            self.vcy[m-1,:,:] = data_input
            
            file_input = "../data_spectral/"+folder+"/ucxx/ucxx_"+str(m)+".csv"
            data_input = np.genfromtxt(file_input, delimiter=',')
            self.ucxx[m-1,:,:] = data_input
            
            file_input = "../data_spectral/"+folder+"/ucyy/ucyy_"+str(m)+".csv"
            data_input = np.genfromtxt(file_input, delimiter=',')
            self.ucyy[m-1,:,:] = data_input
            
            file_input = "../data_spectral/"+folder+"/vcxx/vcxx_"+str(m)+".csv"
            data_input = np.genfromtxt(file_input, delimiter=',')
            self.vcxx[m-1,:,:] = data_input
            
            file_input = "../data_spectral/"+folder+"/vcyy/vcyy_"+str(m)+".csv"
            data_input = np.genfromtxt(file_input, delimiter=',')
            self.vcyy[m-1,:,:] = data_input
            
            file_output = "../data_spectral/"+folder+"/true_shear_stress/t_"+str(m)+".csv"
            data_output = np.genfromtxt(file_output, delimiter=',')
            data_output = data_output.reshape((3,self.nx+1,self.ny+1))
            self.t11[m-1,:,:] = data_output[0,:,:]
            self.t12[m-1,:,:] = data_output[1,:,:]
            self.t22[m-1,:,:] = data_output[2,:,:]
            
            file_input = "../data_spectral/"+folder+"/nu_smag/nus_"+str(m)+".csv"
            data_input = np.genfromtxt(file_input, delimiter=',')
            self.nu[m-1,:,:] = data_input
            
        self.x_train,self.y_train = self.gen_train_data()
        self.x_test,self.y_test = self.gen_test_data()
        
    def gen_train_data(self):
        
        '''
        data generation for training and testing CNN model

        '''
        
        # train data
        for p in range(1,self.n_snapshots_train+1):            
            m = p*self.freq
            nx,ny = self.nx, self.ny
            nt = int((nx-1)*(ny-1))
            
            if self.istencil == 9 and self.ifeatures == 10:
                x_t = np.zeros((nt,90))
            elif self.istencil == 9 and self.ifeatures == 6:
                x_t = np.zeros((nt,54))
            elif self.istencil == 9 and self.ifeatures == 2:
                x_t = np.zeros((nt,18))
            elif self.istencil == 1 and self.ifeatures == 10:
                x_t = np.zeros((nt,10))
            elif self.istencil == 1 and self.ifeatures == 6:
                x_t = np.zeros((nt,6))
            elif self.istencil == 1 and self.ifeatures == 2:
                x_t = np.zeros((nt,2))
            
            if self.ilabel == 1:
                y_t = np.zeros((nt,3))
            elif self.ilabel == 2:
                y_t = np.zeros((nt,1))
            
            n = 0
            
            if istencil == 9 and ifeatures == 10:
                for i in range(1,nx):
                    for j in range(1,ny):
                        x_t[n,0:9] = self.uc[m-1,i-1:i+2,j-1:j+2].flatten()
                        x_t[n,9:18] = self.vc[m-1,i-1:i+2,j-1:j+2].flatten()
                        x_t[n,18:27] = self.ucx[m-1,i-1:i+2,j-1:j+2].flatten()
                        x_t[n,27:36] = self.ucy[m-1,i-1:i+2,j-1:j+2].flatten()
                        x_t[n,36:45] = self.vcx[m-1,i-1:i+2,j-1:j+2].flatten()
                        x_t[n,45:54] = self.vcy[m-1,i-1:i+2,j-1:j+2].flatten()
                        x_t[n,54:63] = self.ucxx[m-1,i-1:i+2,j-1:j+2].flatten()
                        x_t[n,63:72] = self.ucyy[m-1,i-1:i+2,j-1:j+2].flatten()
                        x_t[n,72:81] = self.vcxx[m-1,i-1:i+2,j-1:j+2].flatten()
                        x_t[n,81:90] = self.vcyy[m-1,i-1:i+2,j-1:j+2].flatten()
                        n = n+1
            
            elif istencil == 9 and ifeatures == 6:
                for i in range(1,nx):
                    for j in range(1,ny):
                        x_t[n,0:9] = self.uc[m-1,i-1:i+2,j-1:j+2].flatten()
                        x_t[n,9:18] = self.vc[m-1,i-1:i+2,j-1:j+2].flatten()
                        x_t[n,18:27] = self.ucx[m-1,i-1:i+2,j-1:j+2].flatten()
                        x_t[n,27:36] = self.ucy[m-1,i-1:i+2,j-1:j+2].flatten()
                        x_t[n,36:45] = self.vcx[m-1,i-1:i+2,j-1:j+2].flatten()
                        x_t[n,45:54] = self.vcy[m-1,i-1:i+2,j-1:j+2].flatten()
                        n = n+1
            
            elif istencil == 9 and ifeatures == 2:  
                for i in range(1,nx):
                    for j in range(1,ny):
                        x_t[n,0:9] = self.uc[m-1,i-1:i+2,j-1:j+2].flatten()
                        x_t[n,9:18] = self.vc[m-1,i-1:i+2,j-1:j+2].flatten()
                        n = n+1
            
            elif istencil == 1 and ifeatures == 10:
                for i in range(1,nx):
                    for j in range(1,ny):
                        x_t[n,0] = self.uc[m-1,i,j]
                        x_t[n,1] = self.vc[m-1,i,j]
                        x_t[n,2] = self.ucx[m-1,i,j]
                        x_t[n,3] = self.ucy[m-1,i,j]
                        x_t[n,4] = self.vcx[m-1,i,j]
                        x_t[n,5] = self.vcy[m-1,i,j]
                        x_t[n,6] = self.ucxx[m-1,i,j]
                        x_t[n,7] = self.ucyy[m-1,i,j]
                        x_t[n,8] = self.vcxx[m-1,i,j]
                        x_t[n,9] = self.vcyy[m-1,i,j]
                        n = n+1
            
            elif istencil == 1 and ifeatures == 6:
                for i in range(1,nx):
                    for j in range(1,ny):
                        x_t[n,0] = self.uc[m-1,i,j]
                        x_t[n,1] = self.vc[m-1,i,j]
                        x_t[n,2] = self.ucx[m-1,i,j]
                        x_t[n,3] = self.ucy[m-1,i,j]
                        x_t[n,4] = self.vcx[m-1,i,j]
                        x_t[n,5] = self.vcy[m-1,i,j]
                        n = n+1
                                                
            elif istencil == 1 and ifeatures == 2:
                for i in range(1,nx):
                    for j in range(1,ny):
                        x_t[n,0:9] = self.uc[m-1,i,j]
                        x_t[n,9:18] = self.vc[m-1,i,j]
                        n = n+1
            
            n = 0
            if ilabel == 1:
                for i in range(1,nx):
                    for j in range(1,ny):
                        y_t[n,0], y_t[n,1], y_t[n,2] = self.t11[m-1,i,j], self.t12[m-1,i,j], self.t22[m-1,i,j]
                        n = n+1
                        
            elif ilabel == 2:
                for i in range(1,nx):
                    for j in range(1,ny):
                        y_t[n,0] = self.nu[m-1,i,j]
                        n = n+1       
            
            if p == 1:
                x_train = x_t
                y_train = y_t
            else:
                x_train = np.vstack((x_train,x_t))
                y_train = np.vstack((y_train,y_t))
        
        return x_train, y_train
    
    def gen_test_data(self):
        
        # test data
        m = self.n_snapshots_test
        nx,ny = self.nx, self.ny
        nt = int((nx-1)*(ny-1))

        if self.istencil == 9 and self.ifeatures == 10:
                x_t = np.zeros((nt,90))
        elif self.istencil == 9 and self.ifeatures == 6:
                x_t = np.zeros((nt,54))
        elif self.istencil == 9 and self.ifeatures == 2:
            x_t = np.zeros((nt,18))
        elif self.istencil == 1 and self.ifeatures == 10:
            x_t = np.zeros((nt,10))
        elif self.istencil == 1 and self.ifeatures == 6:
            x_t = np.zeros((nt,6))
        elif self.istencil == 1 and self.ifeatures == 2:
            x_t = np.zeros((nt,2))
        
        if self.ilabel == 1:
            y_t = np.zeros((nt,3))
        elif self.ilabel == 2:
            y_t = np.zeros((nt,1))
        
        n = 0
        
        if istencil == 9 and ifeatures == 10:
            for i in range(1,nx):
                for j in range(1,ny):
                    x_t[n,0:9] = self.uc[m-1,i-1:i+2,j-1:j+2].flatten()
                    x_t[n,9:18] = self.vc[m-1,i-1:i+2,j-1:j+2].flatten()
                    x_t[n,18:27] = self.ucx[m-1,i-1:i+2,j-1:j+2].flatten()
                    x_t[n,27:36] = self.ucy[m-1,i-1:i+2,j-1:j+2].flatten()
                    x_t[n,36:45] = self.vcx[m-1,i-1:i+2,j-1:j+2].flatten()
                    x_t[n,45:54] = self.vcy[m-1,i-1:i+2,j-1:j+2].flatten()
                    x_t[n,54:63] = self.ucxx[m-1,i-1:i+2,j-1:j+2].flatten()
                    x_t[n,63:72] = self.ucyy[m-1,i-1:i+2,j-1:j+2].flatten()
                    x_t[n,72:81] = self.vcxx[m-1,i-1:i+2,j-1:j+2].flatten()
                    x_t[n,81:90] = self.vcyy[m-1,i-1:i+2,j-1:j+2].flatten()
                    n = n+1
        
        elif istencil == 9 and ifeatures == 6:
            for i in range(1,nx):
                for j in range(1,ny):
                    x_t[n,0:9] = self.uc[m-1,i-1:i+2,j-1:j+2].flatten()
                    x_t[n,9:18] = self.vc[m-1,i-1:i+2,j-1:j+2].flatten()
                    x_t[n,18:27] = self.ucx[m-1,i-1:i+2,j-1:j+2].flatten()
                    x_t[n,27:36] = self.ucy[m-1,i-1:i+2,j-1:j+2].flatten()
                    x_t[n,36:45] = self.vcx[m-1,i-1:i+2,j-1:j+2].flatten()
                    x_t[n,45:54] = self.vcy[m-1,i-1:i+2,j-1:j+2].flatten()
                    n = n+1
            
        elif istencil == 9 and ifeatures == 2:  
            for i in range(1,nx):
                for j in range(1,ny):
                    x_t[n,0:9] = self.uc[m-1,i-1:i+2,j-1:j+2].flatten()
                    x_t[n,9:18] = self.vc[m-1,i-1:i+2,j-1:j+2].flatten()
                    n = n+1
        
        elif istencil == 1 and ifeatures == 10:
            for i in range(1,nx):
                for j in range(1,ny):
                    x_t[n,0] = self.uc[m-1,i,j]
                    x_t[n,1] = self.vc[m-1,i,j]
                    x_t[n,2] = self.ucx[m-1,i,j]
                    x_t[n,3] = self.ucy[m-1,i,j]
                    x_t[n,4] = self.vcx[m-1,i,j]
                    x_t[n,5] = self.vcy[m-1,i,j]
                    x_t[n,6] = self.ucxx[m-1,i,j]
                    x_t[n,7] = self.ucyy[m-1,i,j]
                    x_t[n,8] = self.vcxx[m-1,i,j]
                    x_t[n,9] = self.vcyy[m-1,i,j]
                    n = n+1
        
        elif istencil == 1 and ifeatures == 6:
            for i in range(1,nx):
                for j in range(1,ny):
                    x_t[n,0] = self.uc[m-1,i,j]
                    x_t[n,1] = self.vc[m-1,i,j]
                    x_t[n,2] = self.ucx[m-1,i,j]
                    x_t[n,3] = self.ucy[m-1,i,j]
                    x_t[n,4] = self.vcx[m-1,i,j]
                    x_t[n,5] = self.vcy[m-1,i,j]
                    n = n+1                 
                        
        elif istencil == 1 and ifeatures == 2:
            for i in range(1,nx):
                for j in range(1,ny):
                    x_t[n,0:9] = self.uc[m-1,i,j]
                    x_t[n,9:18] = self.vc[m-1,i,j]
                    n = n+1
        
        n = 0
        if ilabel == 1:
            for i in range(1,nx):
                for j in range(1,ny):
                    y_t[n,0], y_t[n,1], y_t[n,2] = self.t11[m-1,i,j], self.t12[m-1,i,j], self.t22[m-1,i,j]
                    n = n+1
                    
        elif ilabel == 2:
            for i in range(1,nx):
                for j in range(1,ny):
                    y_t[n,0] = self.nu[m-1,i,j]
                    n = n+1   
        
        x_test = x_t
        y_test = y_t
        
        return x_test, y_test
    
#%%
# generate training and testing data for CNN
l1 = []
with open('dt.txt') as f:
    for l in f:
        l1.append((l.strip()).split("\t"))

nxf, nyf = np.int64(l1[0][0]), np.int64(l1[0][0])
nx, ny = np.int64(l1[1][0]), np.int64(l1[1][0])
n_snapshots = np.int64(l1[2][0])
n_snapshots_train = np.int64(l1[3][0])   
n_snapshots_test = np.int64(l1[4][0])        
freq = np.int64(l1[5][0])
istencil = np.int64(l1[6][0])    
ifeatures = np.int64(l1[7][0])   
ilabel = np.int64(l1[8][0])      

# hyperparameters initilization
if not os.path.exists("./nn_history/"):
    os.makedirs("./nn_history/")

#%%
obj = DHIT(nx=nx,ny=ny,nxf=nxf,nyf=nyf,freq=freq,n_snapshots=n_snapshots,n_snapshots_train=n_snapshots_train, 
           n_snapshots_test=n_snapshots_test,istencil=istencil,ifeatures=ifeatures,ilabel=ilabel)

data,labels= obj.x_train,obj.y_train
x_test,y_test = obj.x_test,obj.y_test

# scaling between (-1,1)
sc_input = MinMaxScaler(feature_range=(-1,1))
sc_input = sc_input.fit(data)
data_sc = sc_input.transform(data)

sc_output = MinMaxScaler(feature_range=(-1,1))
sc_output = sc_output.fit(labels)
labels_sc = sc_output.transform(labels)

x_test_sc = sc_input.transform(x_test)

x_train, x_valid, y_train, y_valid = train_test_split(data_sc, labels_sc, test_size=0.2 , shuffle= True)

ns_train,nf = x_train.shape
ns_train,nl = y_train.shape 

#%%
# random forest regressor
regressor = DecisionTreeRegressor(max_depth=50, random_state = 0)

training_time_init = tm.time()
regressor.fit(x_train, y_train)
total_training_time = tm.time() - training_time_init

testing_time_init = tm.time()
y_pred_sc = regressor.predict(x_test_sc)
t1 = tm.time() - testing_time_init

testing_time_init = tm.time()
y_pred_sc = regressor.predict(x_test_sc)
t2 = tm.time() - testing_time_init

testing_time_init = tm.time()
y_pred_sc = regressor.predict(x_test_sc)
t3 = tm.time() - testing_time_init


y_pred = sc_output.inverse_transform(y_pred_sc)

with open('cpu_time.csv', 'a', newline='') as myfile:
     wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
     wr.writerow(['DT',istencil, ifeatures, n_snapshots_train, total_training_time, t1, t2, t3])

export_resutls(y_test, y_pred, ilabel, istencil, ifeatures, n_snapshots_train, nxf, nx, nn = 1)

#%%
folder = "data_"+ str(nxf) + "_" + str(nx) 
m = n_snapshots_test
file_input = "../data_spectral/"+folder+"/smag_shear_stress/ts_"+str(m)+".csv"
ts = np.genfromtxt(file_input, delimiter=',')
ts = ts.reshape((3,nx+1,ny+1))
t11s = ts[0,:,:]
t12s = ts[1,:,:]
t22s = ts[2,:,:]

#%%
# histogram plot for shear stresses along with probability density function 
# PDF formula: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.norm.html
num_bins = 64

fig, axs = plt.subplots(1,3,figsize=(13,4))
axs[0].set_yscale('log')
axs[1].set_yscale('log')
axs[2].set_yscale('log')

# the histogram of the data
axs[0].hist(y_test[:,0].flatten(), num_bins, histtype='step', alpha=1, color='r',zorder=5,
                                 linewidth=2.0,range=(-4*np.std(y_test[:,0]),4*np.std(y_test[:,0])),density=True,label="True")

axs[0].hist(t11s.flatten(), num_bins, histtype='step', alpha=1,color='g',zorder=10,
            linewidth=2.0,range=(-4*np.std(y_test[:,0]),4*np.std(y_test[:,0])),density=True,label=r"Dynamic")

axs[0].hist(y_pred[:,0].flatten(), num_bins, histtype='step', alpha=1,color='b',zorder=10,
                                 linewidth=2.0,range=(-4*np.std(y_test[:,0]),4*np.std(y_test[:,0])),density=True,label="DNN")

x_ticks = np.arange(-4*np.std(y_test[:,0]), 4.1*np.std(y_test[:,0]), np.std(y_test[:,0]))                                  
x_labels = [r"${} \sigma$".format(i) for i in range(-4,5)]
axs[0].set_xlabel(r"$\tau_{11}$")
axs[0].set_ylabel("PDF")
axs[0].set_xticks(x_ticks)                                                           
axs[0].set_xticklabels(x_labels)              

#------#
axs[1].hist(y_test[:,1].flatten(), num_bins, histtype='step', alpha=1, color='r',zorder=5,
                                 linewidth=2.0,range=(-4*np.std(y_test[:,1]),4*np.std(y_test[:,1])),density=True,label="True")

axs[1].hist(t12s.flatten(), num_bins, histtype='step', alpha=1,color='g',zorder=10,
            linewidth=2.0,range=(-4*np.std(y_test[:,1]),4*np.std(y_test[:,1])),density=True,label=r"Dynamic")

axs[1].hist(y_pred[:,1].flatten(), num_bins, histtype='step', alpha=1,color='b',zorder=10,
                                 linewidth=2.0,range=(-4*np.std(y_test[:,1]),4*np.std(y_test[:,1])),density=True,label="DNN")

x_ticks = np.arange(-4*np.std(y_test[:,1]), 4.1*np.std(y_test[:,1]), np.std(y_test[:,1]))                                  
x_labels = [r"${} \sigma$".format(i) for i in range(-4,5)]
axs[1].set_xlabel(r"$\tau_{12}$")
#axs[1].set_ylabel("PDF")
axs[1].set_xticks(x_ticks)                                                           
axs[1].set_xticklabels(x_labels)              

#------#
axs[2].hist(y_test[:,2].flatten(), num_bins, histtype='step', alpha=1, color='r',zorder=5,
                                 linewidth=2.0,range=(-4*np.std(y_test[:,2]),4*np.std(y_test[:,2])),density=True,label="True")

axs[2].hist(t22s.flatten(), num_bins, histtype='step', alpha=1,color='g',zorder=10,
            linewidth=2.0,range=(-4*np.std(y_test[:,2]),4*np.std(y_test[:,2])),density=True,label=r"Dynamic")

axs[2].hist(y_pred[:,2].flatten(), num_bins, histtype='step', alpha=1,color='b',zorder=10,
                                 linewidth=2.0,range=(-4*np.std(y_test[:,2]),4*np.std(y_test[:,2])),density=True,label="DNN")

x_ticks = np.arange(-4*np.std(y_test[:,2]), 4.1*np.std(y_test[:,2]), np.std(y_test[:,2]))                                  
x_labels = [r"${} \sigma$".format(i) for i in range(-4,5)]
axs[2].set_xlabel(r"$\tau_{22}$")
#axs[2].set_ylabel("PDF")
axs[2].set_xticks(x_ticks)                                                           
axs[2].set_xticklabels(x_labels)              

fig.tight_layout()
fig.subplots_adjust(hspace=0.5, bottom=0.25)
line_labels = ["True", "DSM", "DT"]
plt.figlegend( line_labels,  loc = 'lower center', borderaxespad=0.3, ncol=3, labelspacing=0.,  prop={'size': 13} )
plt.show()

fig.savefig('nn_history/ts_dt_'+str(istencil)+'_'+str(ifeatures)+'_'+str(n_snapshots_train)+'.pdf', bbox_inches = 'tight')
