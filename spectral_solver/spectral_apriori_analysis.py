#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jul  4 09:37:02 2019

@author: Suraj Pawar


"""

import numpy as np
from scipy.integrate import simps
from numpy.random import seed
seed(1)
import pyfftw
from scipy import integrate
from scipy import linalg
import matplotlib.pyplot as plt 
import time as tm
import matplotlib.ticker as ticker
import os
from numba import jit
import csv

from mpl_toolkits.mplot3d import Axes3D
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.ticker import LinearLocator, FormatStrFormatter
from scipy.interpolate import UnivariateSpline
from matplotlib.colors import LightSource

import seaborn as sns
 
font = {'family' : 'Times New Roman',
        'size'   : 14}    
plt.rc('font', **font)

#%%
def coarsen(nx,ny,nxc,nyc,u):
    
    '''
    coarsen the solution field along with the size of the data 
    
    Inputs
    ------
    nx,ny : number of grid points in x and y direction on fine grid
    nxc,nyc : number of grid points in x and y direction on coarse grid
    u : solution field on fine grid
    
    Output
    ------
    uc : solution field on coarse grid [nxc X nyc]
    '''
    
    uf = np.fft.fft2(u[0:nx,0:ny])
    
    ufc = np.zeros((nxc,nyc),dtype='complex')
    
    ufc [0:int(nxc/2),0:int(nyc/2)] = uf[0:int(nxc/2),0:int(nyc/2)]     
    ufc [int(nxc/2):,0:int(nyc/2)] = uf[int(nx-nxc/2):,0:int(nyc/2)] 
    ufc [0:int(nxc/2),int(nyc/2):] = uf[0:int(nxc/2),int(ny-nyc/2):] 
    ufc [int(nxc/2):,int(nyc/2):] =  uf[int(nx-nxc/2):,int(ny-nyc/2):] 
    
    ufc = ufc*(nxc*nyc)/(nx*ny)
    
    utc = np.real(np.fft.ifft2(ufc))
    
    uc = np.zeros((nxc+1,nyc+1))
    uc[0:nxc,0:nyc] = utc
    uc[:,nyc] = uc[:,0]
    uc[nxc,:] = uc[0,:]
    uc[nxc,nyc] = uc[0,0]
    
    return uc

#%%
def les_filter(nx,ny,nxc,nyc,u):
    
    '''
    coarsen the solution field keeping the size of the data same
    
    Inputs
    ------
    nx,ny : number of grid points in x and y direction on fine grid
    nxc,nyc : number of grid points in x and y direction on coarse grid
    u : solution field on fine grid
    
    Output
    ------
    uc : coarsened solution field [nx X ny]
    '''
    
    uf = np.fft.fft2(u[0:nx,0:ny])
        
    uf[int(nxc/2):int(nx-nxc/2),:] = 0.0
    uf[:,int(nyc/2):int(ny-nyc/2)] = 0.0 
    utc = np.real(np.fft.ifft2(uf))
    
    uc = np.zeros((nx+1,ny+1))
    uc[0:nx,0:ny] = utc
    # periodic bc
    uc[:,ny] = uc[:,0]
    uc[nx,:] = uc[0,:]
    uc[nx,ny] = uc[0,0]
    
    return uc

#%%
def trapezoidal_filter(nx,ny,u):
    
    '''
    coarsen the solution field keeping the size of the data same
    
    Inputs
    ------
    nx,ny : number of grid points in x and y direction on fine grid
    nxc,nyc : number of grid points in x and y direction on coarse grid
    u : solution field on fine grid
    
    Output
    ------
    uc : coarsened solution field [nx X ny]
    '''
    un = np.empty((nx+3,ny+3))
        
    un[1:nx+2,1:ny+2] = u
    un[:,0] = un[:,ny]
    un[:,ny+2] = un[:,2]
    un[0,:] = un[nx,:]
    un[nx+2,:] = un[2,:]
    
    uc = np.zeros((nxc+1,nyc+1))
    uc[:,:] = ( 4.0*un[1:nx+2,1:ny+2] \
                          + 2.0*un[2:nx+3,1:ny+2] \
                          + 2.0*un[0:nx+1,1:ny+2] \
                          + 2.0*un[1:nx+2,2:ny+3] \
                          + 2.0*un[1:nx+2,0:ny+1] \
                          + un[2:nx+3,0:ny+1] \
                          + un[0:nx+1,0:ny+1] \
                          + un[0:nx+1,2:ny+3] \
                          + un[2:nx+3,2:ny+3])/16.0
      
    return uc

#%%
def gaussian_filter(nx,ny,nxc,nyc,u,uc):
    
    '''
    coarsen the solution field keeping the size of the data same
    
    Inputs
    ------
    nx,ny : number of grid points in x and y direction on fine grid
    nxc,nyc : number of grid points in x and y direction on coarse grid
    u : solution field on fine grid
    
    Output
    ------
    uc : coarsened solution field [nx X ny]
    '''
    
    uf = np.fft.fft2(u[0:nx,0:ny])
    
    kx = np.fft.fftfreq(nx,1/nx)
    ky = np.fft.fftfreq(ny,1/ny)
    
    kx = kx.reshape(nx,1)
    ky = ky.reshape(1,ny)
    
    kxc = np.fft.fftfreq(nxc,1/nxc)
    kyc = np.fft.fftfreq(nyc,1/nyc)
    
    sx = np.max(np.abs(kxc))
    sy = np.max(np.abs(kyc))
    s2 = sx**2 + sy**2
    k2 = kx**2 + ky**2
    
    uf = uf*np.exp(-(np.pi**2/24.0)*(k2/s2))
    
    utc = np.fft.ifft2(uf)
    
    uc = np.zeros((nxc+1,nyc+1))
    uc[0:nx,0:ny] = np.real(utc)
    # periodic bc
    uc[:,ny] = uc[:,0]
    uc[nx,:] = uc[0,:]
    uc[nx,ny] = uc[0,0]
    
    return uc
    
#%%
def elliptic_filter(nx,ny,nxc,nyc,u,uc):
    
    '''
    coarsen the solution field keeping the size of the data same using Elliptic filter
    
    Inputs
    ------
    nx,ny : number of grid points in x and y direction on fine grid
    nxc,nyc : number of grid points in x and y direction on coarse grid
    u : solution field on fine grid
    
    Output
    ------
    uc : coarsened solution field [nx X ny]
    '''
    q = 1
    uf = np.fft.fft2(u[0:nx,0:ny])
    
    kx = np.fft.fftfreq(nx,1/nx)
    ky = np.fft.fftfreq(ny,1/ny)
    
    kx = kx.reshape(nx,1)
    ky = ky.reshape(1,ny)
    
    kxc = np.fft.fftfreq(nxc,1/nxc)
    kyc = np.fft.fftfreq(nyc,1/nyc)
    
    sx = np.max(np.abs(kxc))
    sy = np.max(np.abs(kyc))
    s2 = sx**2 + sy**2
    k2 = kx**2 + ky**2
    
    uf = uf/(1.0 + (k2/s2)**q)
    
    utc = np.fft.ifft2(uf)
    
    uc = np.zeros((nxc+1,nyc+1))
    uc[0:nx,0:ny] = np.real(utc)
    # periodic bc
    uc[:,ny] = uc[:,0]
    uc[nx,:] = uc[0,:]
    uc[nx,ny] = uc[0,0]
    
    return uc
    
#%%
def all_filter(nx,ny,nxc,nyc,u,ifltr):
    if ifltr == 1:
        uc = les_filter(nx,ny,nxc,nyc,u)
    elif ifltr == 2:
        uc = trapezoidal_filter(nx,ny,u)
    elif ifltr == 3:
        uc = gaussian_filter(nx,ny,nxc,nyc,u)
    elif ifltr == 4:
        uc = elliptic_filter(nx,ny,nxc,nyc,u)
    
    return uc
    
#%%
def grad_spectral(nx,ny,u):
    
    '''
    compute the gradient of u using spectral differentiation
    
    Inputs
    ------
    nx,ny : number of grid points in x and y direction on fine grid
    u : solution field 
    
    Output
    ------
    ux : du/dx
    uy : du/dy
    '''
    
    ux = np.empty((nx+1,ny+1))
    uy = np.empty((nx+1,ny+1))
    
    uf = np.fft.fft2(u[0:nx,0:ny])

    kx = np.fft.fftfreq(nx,1/nx)
    ky = np.fft.fftfreq(ny,1/ny)
    
    kx = kx.reshape(nx,1)
    ky = ky.reshape(1,ny)
    
    uxf = 1.0j*kx*uf
    uyf = 1.0j*ky*uf 
    
    ux[0:nx,0:ny] = np.real(np.fft.ifft2(uxf))
    uy[0:nx,0:ny] = np.real(np.fft.ifft2(uyf))
    
    # periodic bc
    ux[:,ny] = ux[:,0]
    ux[nx,:] = ux[0,:]
    ux[nx,ny] = ux[0,0]
    
    # periodic bc
    uy[:,ny] = uy[:,0]
    uy[nx,:] = uy[0,:]
    uy[nx,ny] = uy[0,0]
    
    return ux,uy
            

#%%
def write_data(uc,vc,uuc,uvc,vvc,ucx,ucy,vcx,vcy,ucxx,ucyy,vcxx,vcyy,S,t,t_s,C,nu_s,nu_t):
    
    folder = "data_"+ str(nx) + "_" + str(nxc) 
    if not os.path.exists("../data_spectral/"+folder+"/uc"):
        os.makedirs("../data_spectral/"+folder+"/uc")
        os.makedirs("../data_spectral/"+folder+"/vc")
        os.makedirs("../data_spectral/"+folder+"/uuc")
        os.makedirs("../data_spectral/"+folder+"/uvc")
        os.makedirs("../data_spectral/"+folder+"/vvc")
        os.makedirs("../data_spectral/"+folder+"/true_shear_stress")
        os.makedirs("../data_spectral/"+folder+"/smag_shear_stress")
        os.makedirs("../data_spectral/"+folder+"/coefficient")
        os.makedirs("../data_spectral/"+folder+"/nu_smag")
        os.makedirs("../data_spectral/"+folder+"/nu_true")
        os.makedirs("../data_spectral/"+folder+"/ucx")
        os.makedirs("../data_spectral/"+folder+"/ucy")
        os.makedirs("../data_spectral/"+folder+"/vcx")
        os.makedirs("../data_spectral/"+folder+"/vcy")
        os.makedirs("../data_spectral/"+folder+"/ucxx")
        os.makedirs("../data_spectral/"+folder+"/ucyy")
        os.makedirs("../data_spectral/"+folder+"/vcxx")
        os.makedirs("../data_spectral/"+folder+"/vcyy")
        os.makedirs("../data_spectral/"+folder+"/Sc")
        os.makedirs("../data_spectral/"+folder+"/cs2")
        os.makedirs("../data_spectral/"+folder+"/gp/ucx")
        os.makedirs("../data_spectral/"+folder+"/gp/ucy")
        os.makedirs("../data_spectral/"+folder+"/gp/vcx")
        os.makedirs("../data_spectral/"+folder+"/gp/vcy")
        os.makedirs("../data_spectral/"+folder+"/gp/Sc")
        os.makedirs("../data_spectral/"+folder+"/gp/true")
        os.makedirs("../data_spectral/"+folder+"/gp/smag")
        
        with open("../data_spectral/"+folder+"/cs2/cs2.csv", 'a') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerow(['n', 'CS2'])
        
    filename = "../data_spectral/"+folder+"/uc/uc_"+str(int(n))+".csv"
    np.savetxt(filename, uc, delimiter=",")
    filename = "../data_spectral/"+folder+"/vc/vc_"+str(int(n))+".csv"
    np.savetxt(filename, vc, delimiter=",")
    filename = "../data_spectral/"+folder+"/uuc/uuc_"+str(int(n))+".csv"
    np.savetxt(filename, uuc, delimiter=",")
    filename = "../data_spectral/"+folder+"/uvc/uvc_"+str(int(n))+".csv"
    np.savetxt(filename, uvc, delimiter=",")
    filename = "../data_spectral/"+folder+"/vvc/vvc_"+str(int(n))+".csv"
    np.savetxt(filename, vvc, delimiter=",")
    filename = "../data_spectral/"+folder+"/coefficient/c_"+str(int(n))+".csv"
    np.savetxt(filename, C, delimiter=",")
    filename = "../data_spectral/"+folder+"/nu_smag/nus_"+str(int(n))+".csv"
    np.savetxt(filename, nu_s, delimiter=",")
    filename = "../data_spectral/"+folder+"/ucx/ucx_"+str(int(n))+".csv"
    np.savetxt(filename, ucx, delimiter=",")
    filename = "../data_spectral/"+folder+"/ucy/ucy_"+str(int(n))+".csv"
    np.savetxt(filename, ucy, delimiter=",")
    filename = "../data_spectral/"+folder+"/vcx/vcx_"+str(int(n))+".csv"
    np.savetxt(filename, vcx, delimiter=",")
    filename = "../data_spectral/"+folder+"/vcy/vcy_"+str(int(n))+".csv"
    np.savetxt(filename, vcy, delimiter=",")
    filename = "../data_spectral/"+folder+"/ucxx/ucxx_"+str(int(n))+".csv"
    np.savetxt(filename, ucxx, delimiter=",")
    filename = "../data_spectral/"+folder+"/ucyy/ucyy_"+str(int(n))+".csv"
    np.savetxt(filename, ucyy, delimiter=",")
    filename = "../data_spectral/"+folder+"/vcxx/vcxx_"+str(int(n))+".csv"
    np.savetxt(filename, vcxx, delimiter=",")
    filename = "../data_spectral/"+folder+"/vcyy/vcyy_"+str(int(n))+".csv"
    np.savetxt(filename, vcyy, delimiter=",")
    filename = "../data_spectral/"+folder+"/Sc/Sc_"+str(int(n))+".csv"
    np.savetxt(filename, S, delimiter=",")
    
    with open("../data_spectral/"+folder+"/cs2/cs2.csv", 'a') as csvFile:
            writer = csv.writer(csvFile)
            writer.writerow([str(n), str(np.mean(C))])
        
    with open("../data_spectral/"+folder+"/true_shear_stress/t_"+str(int(n))+".csv", 'w') as outfile:
        outfile.write('# Array shape: {0}\n'.format(t.shape))
        for data_slice in t:
            np.savetxt(outfile, data_slice, delimiter=",")
            outfile.write('# New slice\n')
    
    with open("../data_spectral/"+folder+"/smag_shear_stress/ts_"+str(int(n))+".csv", 'w') as outfile:
        outfile.write('# Array shape: {0}\n'.format(t_s.shape))
        for data_slice in t_s:
            np.savetxt(outfile, data_slice, delimiter=",")
            outfile.write('# New slice\n')
    
    with open("../data_spectral/"+folder+"/nu_true/nut_"+str(int(n))+".csv", 'w') as outfile:
        outfile.write('# Array shape: {0}\n'.format(nu_t.shape))
        for data_slice in nu_t:
            np.savetxt(outfile, data_slice, delimiter=",")
            outfile.write('# New slice\n')
                          
    filename = "../data_spectral/"+folder+"/gp/ucx/ucx_"+str(int(n))+".npy"
    np.save(filename, ucx)
    filename = "../data_spectral/"+folder+"/gp/ucy/ucy_"+str(int(n))+".npy"
    np.save(filename, ucy)
    filename = "../data_spectral/"+folder+"/gp/vcx/vcx_"+str(int(n))+".npy"
    np.save(filename, vcx)
    filename = "../data_spectral/"+folder+"/gp/vcy/vcy_"+str(int(n))+".npy"
    np.save(filename, vcy)
    filename = "../data_spectral/"+folder+"/gp/Sc/Sc_"+str(int(n))+".npy"
    np.save(filename, S)
    filename = "../data_spectral/"+folder+"/gp/true/t_"+str(int(n))+".npy"
    np.save(filename, t.reshape(int(3*(nxc+1)),int(nyc+1)))
    filename = "../data_spectral/"+folder+"/gp/smag/ts_"+str(int(n))+".npy"
    np.save(filename, t_s.reshape(int(3*(nxc+1)),int(nyc+1)))

#%%
def write_data_dyn(L,M):
    
    folder = "data_"+ str(nx) + "_" + str(nxc) 
    if not os.path.exists("../data_spectral/"+folder+"/L"):
        os.makedirs("../data_spectral/"+folder+"/L")
        os.makedirs("../data_spectral/"+folder+"/M")   
    
    filename = "../data_spectral/"+folder+"/L/L_"+str(int(n))+".csv"
    np.savetxt(filename, L, delimiter=",")
    filename = "../data_spectral/"+folder+"/M/M_"+str(int(n))+".csv"
    np.savetxt(filename, M, delimiter=",")
    
    
#%%
def bardina_stres1(nx,ny,nxc,nyc,u,v):
    
    ul = np.empty((nx+1,ny+1))
    vl = np.empty((nx+1,ny+1))
    uc = np.empty((nxc+1,nyc+1))
    vc = np.empty((nxc+1,nyc+1))
    uuc = np.empty((nxc+1,nyc+1))
    uvc = np.empty((nxc+1,nyc+1))
    vvc = np.empty((nxc+1,nyc+1))
    
    all_filter(nx,ny,nxc,nyc,u,ul,ifltr) # ul has same dimension as u
    all_filter(nx,ny,nxc,nyc,v,vl,ifltr) # vl has same dimension as v
    
    uul = ul*ul
    uvl = ul*vl
    vvl = vl*vl
    
    coarsen(nx,ny,nxc,nyc,ul,uc)
    coarsen(nx,ny,nxc,nyc,vl,vc)
    coarsen(nx,ny,nxc,nyc,uul,uuc)
    coarsen(nx,ny,nxc,nyc,uvl,uvc)
    coarsen(nx,ny,nxc,nyc,vvl,vvc)
       
    t11_b = uuc - uc*uc
    t12_b = uvc - uc*vc
    t22_b = vvc - vc*vc
    
    return t11_b, t12_b, t22_b

#%%
def bardina_stres2(nxc,nyc,uc,vc):
    
    alpha = 2
    nxcc = int(nxc/alpha)
    nycc = int(nyc/alpha)
    
    ucc = np.empty((nxc+1,nyc+1))
    vcc = np.empty((nxc+1,nyc+1))
    uucc = np.empty((nxc+1,nyc+1))
    uvcc = np.empty((nxc+1,nyc+1))
    vvcc = np.empty((nxc+1,nyc+1))
    
    all_filter(nxc,nyc,nxcc,nycc,uc,ucc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,vc,vcc,ifltr)
    
    uuc = uc*uc
    uvc = uc*vc
    vvc = vc*vc
    
    all_filter(nxc,nyc,nxcc,nycc,uuc,uucc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,uvc,uvcc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,vvc,vvcc,ifltr)
    
    t11_b = uucc - ucc*ucc
    t12_b = uvcc - ucc*vcc
    t22_b = vvcc - vcc*vcc

    return t11_b, t12_b, t22_b    
         
#%%
def compute_cs_smag(dxc,dyc,nxc,nyc,uc,vc,dac,d11c,d12c,d22c,ics,ifltr,alpha):
    
    '''
    compute the Smagorinsky coefficient (dynamic: Germano, Lilys; static)
    
    Inputs
    ------
    dxc,dyc : grid spacing in x and y direction on coarse grid
    nxc,nyc : number of grid points in x and y direction on coarse grid
    uc : x-direction velocity on coarse grid
    vc : y-direction velocity on coarse grid
    dac : |S| 
    d11c : S11 (du/dx)
    d12c : S12 ((du/dy + dv/dx)/2)
    d22c : S22 (dv/dy)
    
    Output
    ------
    CS2 : square of Smagorinsky coefficient
    '''
    
    nxcc = int(nxc/alpha)
    nycc = int(nyc/alpha)
    
    dcs_time_init = tm.time()
    
    dacc = np.empty((nxc+1,nyc+1))
    d11cc = np.empty((nxc+1,nyc+1))
    d12cc = np.empty((nxc+1,nyc+1))
    d22cc = np.empty((nxc+1,nyc+1))

    uuc = uc*uc
    uvc = uc*vc
    vvc = vc*vc
    
    uucc = all_filter(nxc,nyc,nxcc,nycc,uuc,ifltr)
    uvcc = all_filter(nxc,nyc,nxcc,nycc,uvc,ifltr)
    vvcc = all_filter(nxc,nyc,nxcc,nycc,vvc,ifltr)
      
    ucc = all_filter(nxc,nyc,nxcc,nycc,uc,ifltr)
    vcc = all_filter(nxc,nyc,nxcc,nycc,vc,ifltr)
        
    uccx,uccy = grad_spectral(nxc,nyc,ucc)
    vccx,vccy = grad_spectral(nxc,nyc,vcc)
    
    #dacc = np.sqrt(2.0*ucx*ucx + 2.0*vcy*vcy + (ucy+vcx)*(ucy+vcx))
    dacc = np.sqrt((uccx-vccy)**2 + (uccy+vccx)**2)
    d11cc = uccx
    d12cc = 0.5*(uccy+vccx)
    d22cc = vccy
    
    h11c = dac*d11c
    h12c = dac*d12c
    h22c = dac*d22c
    
    h11cc = all_filter(nxc,nyc,nxcc,nycc,h11c,ifltr)
    h12cc = all_filter(nxc,nyc,nxcc,nycc,h12c,ifltr)
    h22cc = all_filter(nxc,nyc,nxcc,nycc,h22c,ifltr)
    
    delta = np.sqrt(dxc*dyc)
    
    l11 = uucc - ucc*ucc
    l12 = uvcc - ucc*vcc
    l22 = vvcc - vcc*vcc
    
    l11d = l11 - 0.5*(l11 + l22)
    l12d = l12
    l22d = l22 - 0.5*(l11 + l22)
    
    m11 = delta**2*(h11cc-alpha**2*dacc*d11cc)
    m12 = delta**2*(h12cc-alpha**2*dacc*d12cc)
    m22 = delta**2*(h22cc-alpha**2*dacc*d22cc)
    
    aa = (l11d*m11 + 2.0*(l12d*m12) + l22d*m22)
    bb = (m11*m11 + 2.0*(m12*m12) + m22*m22)
    
    if ics == 1:
        write_data_dyn(aa,bb)
#        CS2 = (aa)/(2.0*bb)  #Germano
#        x = np.linspace(0.0,2.0*np.pi,nxc+1)
#        y = np.linspace(0.0,2.0*np.pi,nxc+1)
#        ai = simps(simps(aa + abs(aa),y),x)
#        bi = simps(simps(bb,y),x)
#        CS2 = (ai/bi)*np.ones((nxc+1,nyc+1))
        CS2 = (np.sum(0.5*(aa + abs(aa)))/np.sum(bb))*np.ones((nxc+1,nyc+1))
        dcs_time = tm.time() - dcs_time_init
        print(n, " ", dcs_time)
        
    elif ics == 2:
        #CS2 = 0.04*np.ones((nxc+1,nyc+1)) # constant
        CS2 = 0.18**2*np.ones((nxc+1,nyc+1)) # constant
    
    return CS2

#%%
def compute_stress_smag(nx,ny,nxc,nyc,dxc,dyc,u,v,n,ist,ics,ifltr,alpha):
    
    '''
    compute the true stresses and Smagorinsky stresses
    
    Inputs
    ------
    nx,ny : number of grid points in x and y direction on fine grid
    nxc,nyc : number of grid points in x and y direction on coarse grid
    dxc,dyc : grid spacing in x and y direction    
    u : x-direction velocity on fine grid
    v : y-direction velocity on fine grid
    n : time-step
    
    Output
    ------
    uc, vc, uuc, uvc, vvc, t, ts
    '''

    t11 = np.empty((nxc+1,nyc+3))
    t12 = np.empty((nxc+1,nyc+1))
    t22 = np.empty((nxc+1,nyc+1))
    t11_s = np.empty((nxc+1,nyc+1))
    t12_s = np.empty((nxc+1,nyc+1))
    t22_s = np.empty((nxc+1,nyc+1))
    t = np.empty((3,nxc+1,nyc+1)) # true shear stress
    t_s = np.empty((3,nxc+1,nyc+1)) # Smagorinsky shear stress
    nu_t = np.empty((3,nxc+1,nyc+1)) # true viscosity
    
    uu = np.empty((nx+1,ny+1))
    uv = np.empty((nx+1,ny+1))
    vv = np.empty((nx+1,ny+1))
    
    uu = u*u
    uv = u*v
    vv = v*v
    
    uc = coarsen(nx,ny,nxc,nyc,u)
    vc = coarsen(nx,ny,nxc,nyc,v)
    uuc = coarsen(nx,ny,nxc,nyc,uu)
    uvc = coarsen(nx,ny,nxc,nyc,uv)
    vvc = coarsen(nx,ny,nxc,nyc,vv)
    
    #True (deviatoric stress)
    t11 = uuc -uc*uc
    t12 = uvc -uc*vc
    t22 = vvc -vc*vc
    
    t11d = t11 - 0.5*(t11+t22)
    t22d = t22 - 0.5*(t11+t22)
       
    t[0,:,:] = t11d
    t[1,:,:] = t12
    t[2,:,:] = t22d
    
    dsm_time_init = tm.time()
    
    #Smagorinsky
    delta = np.sqrt(dxc*dyc)
    
    ucx,ucy = grad_spectral(nxc,nyc,uc)
    vcx,vcy = grad_spectral(nxc,nyc,vc)
      
    d11 = ucx
    d12 = 0.5*(ucy+vcx)
    d22 = vcy
    
    da = np.sqrt((ucx-vcy)**2 + (ucy+vcx)**2) # |S| 
    
    if ist == 1:
        CS2 = compute_cs_smag(dxc,dyc,nxc,nyc,uc,vc,da,d11,d12,d22,ics,ifltr,alpha) # for Smagorinsky
        nu_s = CS2*delta**2*da
        
        dsm_time = tm.time() - dsm_time_init
        
        print(n, " CS = ", np.mean((CS2)), " ", dsm_time)

        t11_s = - 2.0*CS2*delta**2*da*d11
        t12_s = - 2.0*CS2*delta**2*da*d12
        t22_s = - 2.0*CS2*delta**2*da*d22
        
        t_s[0,:,:] = t11_s
        t_s[1,:,:] = t12_s
        t_s[2,:,:] = t22_s
    
    elif ist == 5:
        print(n)        
        
        t11_b,t12_b,t22_b = bardina_stres2(nxc,nyc,uc,vc)
               
        t_s[0,:,:] = t11_b - 0.5*(t11_b+t22_b)
        t_s[1,:,:] = t12_b
        t_s[2,:,:] = t22_b - 0.5*(t11_b+t22_b)
    
    # true viscosity
    nu_t[0,:,:] = t11d/d11
    nu_t[1,:,:] = t12/d12
    nu_t[2,:,:] = t22d/d22
    
    # compute second-order derivative
    ucxx,ucxy = grad_spectral(nxc,nyc,ucx)
    ucyx,ucyy = grad_spectral(nxc,nyc,ucy) 
    vcxx,vcxy = grad_spectral(nxc,nyc,vcx)
    vcyx,vcyy = grad_spectral(nxc,nyc,vcy) 

    write_data(uc,vc,uuc,uvc,vvc,ucx,ucy,vcx,vcy,ucxx,ucyy,vcxx,vcyy,da,t,t_s,CS2,nu_s,nu_t)
    
#%%
def compute_cs_leith(dxc,dyc,nxc,nyc,uc,vc,Wc,d11c,d12c,d22c,ics,ifltr,alpha):
    
    '''
    compute the Smagorinsky coefficient (dynamic: Germano, Lilys; static)
    
    Inputs
    ------
    dxc,dyc : grid spacing in x and y direction on coarse grid
    nxc,nyc : number of grid points in x and y direction on coarse grid
    uc : x-direction velocity on coarse grid
    vc : y-direction velocity on coarse grid
    dac : |S| 
    d11c : S11 (du/dx)
    d12c : S12 ((du/dy + dv/dx)/2)
    d22c : S22 (dv/dy)
    
    Output
    ------
    CS2 : square of Smagorinsky coefficient
    '''

    nxcc = int(nxc/alpha)
    nycc = int(nyc/alpha)
    ucc = np.empty((nxc+1,nyc+1))
    vcc = np.empty((nxc+1,nyc+1))
    uucc = np.empty((nxc+1,nyc+1))
    uvcc = np.empty((nxc+1,nyc+1))
    vvcc = np.empty((nxc+1,nyc+1))
    
    Wcc = np.empty((nxc+1,nyc+1))
    d11cc = np.empty((nxc+1,nyc+1))
    d12cc = np.empty((nxc+1,nyc+1))
    d22cc = np.empty((nxc+1,nyc+1))
    h11cc = np.empty((nxc+1,nyc+1))
    h12cc = np.empty((nxc+1,nyc+1))
    h22cc = np.empty((nxc+1,nyc+1))

        
    all_filter(nxc,nyc,nxcc,nycc,uc,ucc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,vc,vcc,ifltr)
    
    uuc = uc*uc
    vvc = vc*vc
    uvc = uc*vc
    
    ucx,ucy = grad_spectral(nxc,nyc,ucc)
    vcx,vcy = grad_spectral(nxc,nyc,vcc)
    
    all_filter(nxc,nyc,nxcc,nycc,uuc,uucc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,uvc,uvcc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,vvc,vvcc,ifltr)
    
    wcc = vcx - ucy
    wccx,wccy = grad_spectral(nxc,nyc,wcc)    
    Wcc = np.sqrt(wccx*wccx + wccy*wccy)

    d11cc = ucx
    d12cc = 0.5*(ucy+vcx)
    d22cc = vcy
  
    h11c = Wc*d11c
    h12c = Wc*d12c
    h22c = Wc*d22c
    
    all_filter(nxc,nyc,nxcc,nycc,h11c,h11cc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,h12c,h12cc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,h22c,h22cc,ifltr)
    
    l11 = uucc - ucc*ucc
    l12 = uvcc - ucc*vcc
    l22 = vvcc - vcc*vcc
    
    l11d = l11 - 0.5*(l11 + l22)
    l12d = l12
    l22d = l22 - 0.5*(l11 + l22)
    
    delta = np.sqrt(dxc*dyc)
    
    m11 = 2.0*delta**3*(h11cc-alpha**3*np.abs(Wcc)*d11cc)
    m12 = 2.0*delta**3*(h12cc-alpha**3*np.abs(Wcc)*d12cc)
    m22 = 2.0*delta**3*(h22cc-alpha**3*np.abs(Wcc)*d22cc)
    
    aa = (l11d*m11 + 2.0*(l12d*m12) + l22d*m22)
    bb = (m11*m11 + 2.0*(m12*m12) + m22*m22)
    
    if ics == 1:
        #CL3 = aa/bb  # dynamic
        #CL3 = CL3.clip(0.0)
        CL3 = (np.sum(aa)/np.sum(bb))*np.ones((nxc+1,nyc+1))
        #CL3 = (np.sum(np.abs(aa))/np.sum(np.abs(bb)))*np.ones((nxc+1,nyc+1))
    
    elif ics == 2:
        CL3 = 0.11**3*np.ones((nxc+1,nyc+1)) # constant
    
    return CL3

#%%
def compute_stress_leith(nx,ny,nxc,nyc,dxc,dyc,u,v,n,ist,ics,ifltr,alpha):
    
    '''
    compute the true stresses and Smagorinsky stresses
    
    Inputs
    ------
    nx,ny : number of grid points in x and y direction on fine grid
    nxc,nyc : number of grid points in x and y direction on coarse grid
    dxc,dyc : grid spacing in x and y direction    
    u : x-direction velocity on fine grid
    v : y-direction velocity on fine grid
    n : time-step
    
    Output
    ------
    uc, vc, uuc, uvc, vvc, t, ts
    '''
    
    t11 = np.empty((nxc+1,nyc+3))
    t12 = np.empty((nxc+1,nyc+1))
    t22 = np.empty((nxc+1,nyc+1))
    t11_s = np.empty((nxc+1,nyc+1))
    t12_s = np.empty((nxc+1,nyc+1))
    t22_s = np.empty((nxc+1,nyc+1))
    t = np.empty((3,nxc+1,nyc+1)) # true shear stress
    t_s = np.empty((3,nxc+1,nyc+1)) # Smagorinsky shear stress
    
    uu = np.empty((nx+1,ny+1))
    uv = np.empty((nx+1,ny+1))
    vv = np.empty((nx+1,ny+1))
    
    ux = np.empty((nxc+1,nyc+1))
    uy = np.empty((nxc+1,nyc+1))
    vx = np.empty((nxc+1,nyc+1))
    vy = np.empty((nxc+1,nyc+1))
    
    wc = np.empty((nxc+1,nyc+1))
    
    uu = u*u
    uv = u*v
    vv = v*v
    
    uc = coarsen(nx,ny,nxc,nyc,u)
    vc = coarsen(nx,ny,nxc,nyc,v)
    uuc = coarsen(nx,ny,nxc,nyc,uu)
    uvc = coarsen(nx,ny,nxc,nyc,uv)
    vvc = coarsen(nx,ny,nxc,nyc,vv)
    
    #True (deviatoric stress)
    t11 = uuc -uc*uc
    t12 = uvc -uc*vc
    t22 = vvc -vc*vc
    
    t11d = t11 - 0.5*(t11+t22)
    t22d = t22 - 0.5*(t11+t22)
    
    t[0,:,:] = t11d
    t[1,:,:] = t12
    t[2,:,:] = t22d

    delta = np.sqrt(dxc*dyc)
    
    ux,uy = grad_spectral(nxc,nyc,uc)
    vx,vy = grad_spectral(nxc,nyc,vc)
    
    wc = vx - uy
    
    wcx,wcy = grad_spectral(nxc,nyc,wc)
    
    W = np.sqrt(wcx*wcx + wcy*wcy)
      
    d11 = ux
    d12 = 0.5*(uy+vx)
    d22 = vy  
    
    CL3 = compute_cs_leith(dxc,dyc,nxc,nyc,uc,vc,W,d11,d12,d22,ics,ifltr,alpha) # for Smagorinsky
    
    nu = CL3*delta**3*W
    
    print(n, " CL = ", np.max(CL3), " ", np.min(CL3), 
          " ", np.mean((CL3)), " ", np.std((CL3)))
       
    t11_s = - 2.0*CL3*delta**3*W*d11
    t12_s = - 2.0*CL3*delta**3*W*d12
    t22_s = - 2.0*CL3*delta**3*W*d22
    
    t_s[0,:,:] = t11_s
    t_s[1,:,:] = t12_s
    t_s[2,:,:] = t22_s
    
    write_data(uc,vc,uuc,uvc,vvc,ux,uy,vx,vy,W,t,t_s,CL3,nu)

#%%
def compute_cs_horiuti(dxc,dyc,nxc,nyc,uc,vc,a11c,a12c,a22c,ics,ifltr,ihr,alpha):
    
    '''
    compute the Smagorinsky coefficient (dynamic: Germano, Lilys; static)
    
    Inputs
    ------
    dxc,dyc : grid spacing in x and y direction on coarse grid
    nxc,nyc : number of grid points in x and y direction on coarse grid
    uc : x-direction velocity on coarse grid
    vc : y-direction velocity on coarse grid
    dac : |S| 
    d11c : S11 (du/dx)
    d12c : S12 ((du/dy + dv/dx)/2)
    d22c : S22 (dv/dy)
    
    Output
    ------
    CS2 : square of Smagorinsky coefficient
    '''

    nxcc = int(nxc/alpha)
    nycc = int(nyc/alpha)
    ucc = np.empty((nxc+1,nyc+1))
    vcc = np.empty((nxc+1,nyc+1))
    uucc = np.empty((nxc+1,nyc+1))
    uvcc = np.empty((nxc+1,nyc+1))
    vvcc = np.empty((nxc+1,nyc+1))

    a11cc = np.empty((nxc+1,nyc+1))
    a12cc = np.empty((nxc+1,nyc+1))
    a22cc = np.empty((nxc+1,nyc+1))
    p11cc = np.empty((nxc+1,nyc+1))
    p12cc = np.empty((nxc+1,nyc+1))
    p22cc = np.empty((nxc+1,nyc+1))

        
    all_filter(nxc,nyc,nxcc,nycc,uc,ucc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,vc,vcc,ifltr)
    
    uuc = uc*uc
    vvc = vc*vc
    uvc = uc*vc
    
    all_filter(nxc,nyc,nxcc,nycc,uuc,uucc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,uvc,uvcc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,vvc,vvcc,ifltr)
    
    uccx,uccy = grad_spectral(nxc,nyc,ucc)
    vccx,vccy = grad_spectral(nxc,nyc,vcc)
    
    all_filter(nxc,nyc,nxcc,nycc,a11c,a11cc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,a12c,a12cc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,a22c,a22cc,ifltr)
    
    if ihr == 1:
        p11cc = 0.5*(uccy+vccx)*(vccx-uccy)
        p12cc = 0.5*(vccy-uccx)*(vccx-uccy)
        p22cc = -0.5*(uccy+vccx)*(vccx-uccy)
    elif ihr == 2:
        p11cc = -uccx**2 - 0.5*vccx**2 - 0.5*uccy**2
        p12cc = -0.5*(uccy+vccx)*(uccx+vccy)
        p22cc = -vccy**2 - 0.5*vccx**2 - 0.5*uccy**2
    elif ihr == 3:
        p11cc = 0.5*(uccy+vccx)*(vccx-uccy) - uccx**2 - 0.5*vccx**2 - 0.5*uccy**2
        p12cc = 0.5*(vccy-uccx)*(vccx-uccy) - 0.5*(uccy+vccx)*(uccx+vccy)
        p22cc = -0.5*(uccy+vccx)*(vccx-uccy) - vccy**2 - 0.5*vccx**2 - 0.5*uccy**2
       
    l11 = uucc - ucc*ucc
    l12 = uvcc - ucc*vcc
    l22 = vvcc - vcc*vcc
    
    l11d = l11 - 0.5*(l11 + l22)
    l12d = l12
    l22d = l12 - 0.5*(l11 + l22)
    
    delta = np.sqrt(dxc*dyc)
    
    m11 = 2.0*delta**2*(a11cc-alpha**2*p11cc)
    m12 = 2.0*delta**2*(a12cc-alpha**2*p12cc)
    m22 = 2.0*delta**2*(a22cc-alpha**2*p22cc)
    
    a = (l11d*m11 + 2.0*(l12d*m12) + l22d*m22)
    b = (m11*m11 + 2.0*(m12*m12) + m22*m22)
    
    if ics == 1:
        CH2 = a/b  # dynamic
    
    elif ics == 2:
        CH2 = 1/24.0*np.ones((nxc+1,nyc+1)) # constant
        #CH2 = 0.03*np.ones((nxc+1,nyc+1)) # constant
        
    return CH2

#%%
def compute_stress_horiuti(nx,ny,nxc,nyc,dxc,dyc,u,v,n,ist,ics,ifltr,ihr,alpha):
    
    '''
    compute the true stresses and Smagorinsky stresses
    
    Inputs
    ------
    nx,ny : number of grid points in x and y direction on fine grid
    nxc,nyc : number of grid points in x and y direction on coarse grid
    dxc,dyc : grid spacing in x and y direction    
    u : x-direction velocity on fine grid
    v : y-direction velocity on fine grid
    n : time-step
    
    Output
    ------
    uc, vc, uuc, uvc, vvc, t, ts
    '''
    
    t11 = np.empty((nxc+1,nyc+3))
    t12 = np.empty((nxc+1,nyc+1))
    t22 = np.empty((nxc+1,nyc+1))
    t11_s = np.empty((nxc+1,nyc+1))
    t12_s = np.empty((nxc+1,nyc+1))
    t22_s = np.empty((nxc+1,nyc+1))
    t = np.empty((3,nxc+1,nyc+1)) # true shear stress
    t_s = np.empty((3,nxc+1,nyc+1)) # Smagorinsky shear stress
    
    uu = np.empty((nx+1,ny+1))
    uv = np.empty((nx+1,ny+1))
    vv = np.empty((nx+1,ny+1))
    
    ux = np.empty((nxc+1,nyc+1))
    uy = np.empty((nxc+1,nyc+1))
    vx = np.empty((nxc+1,nyc+1))
    vy = np.empty((nxc+1,nyc+1))
   
    uu = u*u
    uv = u*v
    vv = v*v
    
    uc = coarsen(nx,ny,nxc,nyc,u)
    vc = coarsen(nx,ny,nxc,nyc,v)
    uuc = coarsen(nx,ny,nxc,nyc,uu)
    uvc = coarsen(nx,ny,nxc,nyc,uv)
    vvc = coarsen(nx,ny,nxc,nyc,vv)
    
    #True (deviatoric stress)
    t11 = uuc -uc*uc
    t12 = uvc -uc*vc
    t22 = vvc -vc*vc
    
    t11d = t11 - 0.5*(t11+t22)
    t22d = t22 - 0.5*(t11+t22)
    
    t[0,:,:] = t11d
    t[1,:,:] = t12
    t[2,:,:] = t22d
    
    delta = np.sqrt(dxc*dyc)
    
    ux,uy = grad_spectral(nxc,nyc,uc)
    vx,vy = grad_spectral(nxc,nyc,vc)
    
    if ihr == 1:
        a11 = 0.5*(uy+vx)*(vx-uy)
        a12 = 0.5*(vy-ux)*(vx-uy)
        a22 = -0.5*(uy+vx)*(vx-uy)
    elif ihr == 2:
        a11 = -ux**2 - 0.5*vx**2 - 0.5*uy**2
        a12 = -0.5*(uy+vx)*(ux+vy)
        a22 = -vy**2 - 0.5*vx**2 - 0.5*uy**2
    elif ihr == 3:
        a11 = 0.5*(uy+vx)*(vx-uy) -ux**2 - 0.5*vx**2 - 0.5*uy**2
        a12 = 0.5*(vy-ux)*(vx-uy) -0.5*(uy+vx)*(ux+vy)
        a22 = -0.5*(uy+vx)*(vx-uy) -vy**2 - 0.5*vx**2 - 0.5*uy**2
        
        
    CH2 = compute_cs_horiuti(dxc,dyc,nxc,nyc,uc,vc,a11,a12,a22,ics,ifltr,ihr,alpha) # for Smagorinsky
    
    nu = CH2*delta**2
    
    print(n, " CH = ", np.max(CH2), " ", np.min(CH2),
          " ", np.mean((CH2)), " ", np.std((CH2)))
       
    t11_s = - 2.0*CH2*delta**2*a11
    t12_s = - 2.0*CH2*delta**2*a12
    t22_s = - 2.0*CH2*delta**2*a22
    
    t_s[0,:,:] = t11_s
    t_s[1,:,:] = t12_s
    t_s[2,:,:] = t22_s
    
    write_data(uc,vc,uuc,uvc,vvc,ux,uy,vx,vy,a11,t,t_s,CH2,nu)
    
#%%
def compute_cs_hybrid(dxc,dyc,nxc,nyc,uc,vc,dac,d11c,d12c,d22c,Wc,a11c,a12c,a22c,ics,ifltr,alpha):
    
    '''
    compute the Smagorinsky coefficient (dynamic: Germano, Lilys; static)
    
    Inputs
    ------
    dxc,dyc : grid spacing in x and y direction on coarse grid
    nxc,nyc : number of grid points in x and y direction on coarse grid
    uc : x-direction velocity on coarse grid
    vc : y-direction velocity on coarse grid
    dac : |S| 
    d11c : S11 (du/dx)
    d12c : S12 ((du/dy + dv/dx)/2)
    d22c : S22 (dv/dy)
    
    Output
    ------
    CS2 : square of Smagorinsky coefficient
    '''
    
    alpha = 1.6
    nxcc = int(nxc/alpha)
    nycc = int(nyc/alpha)
    ucc = np.empty((nxc+1,nyc+1))
    vcc = np.empty((nxc+1,nyc+1))
    uucc = np.empty((nxc+1,nyc+1))
    uvcc = np.empty((nxc+1,nyc+1))
    vvcc = np.empty((nxc+1,nyc+1))
    
    # Smagorinsky 
    dacc = np.empty((nxc+1,nyc+1))
    d11cc = np.empty((nxc+1,nyc+1))
    d12cc = np.empty((nxc+1,nyc+1))
    d22cc = np.empty((nxc+1,nyc+1))
    q11cc = np.empty((nxc+1,nyc+1))
    q12cc = np.empty((nxc+1,nyc+1))
    q22cc = np.empty((nxc+1,nyc+1))
    
    # Leith 
    Wcc = np.empty((nxc+1,nyc+1))
    h11cc = np.empty((nxc+1,nyc+1))
    h12cc = np.empty((nxc+1,nyc+1))
    h22cc = np.empty((nxc+1,nyc+1))
    
    # Horiuti parameters
    a11cc = np.empty((nxc+1,nyc+1))
    a12cc = np.empty((nxc+1,nyc+1))
    a22cc = np.empty((nxc+1,nyc+1))
    p11cc = np.empty((nxc+1,nyc+1))
    p12cc = np.empty((nxc+1,nyc+1))
    p22cc = np.empty((nxc+1,nyc+1))

    all_filter(nxc,nyc,nxcc,nycc,uc,ucc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,vc,vcc,ifltr)
    
    uuc = uc*uc
    vvc = vc*vc
    uvc = uc*vc
    
    all_filter(nxc,nyc,nxcc,nycc,uuc,uucc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,uvc,uvcc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,vvc,vvcc,ifltr)
    
    uccx,uccy = grad_spectral(nxc,nyc,ucc)
    vccx,vccy = grad_spectral(nxc,nyc,vcc)
        
    delta = np.sqrt(dxc*dyc)
    
    # Smagorinsky
    q11c = dac*d11c
    q12c = dac*d12c
    q22c = dac*d22c
    
    all_filter(nxc,nyc,nxcc,nycc,dac,dacc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,d11c,d11cc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,d12c,d12cc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,d22c,d22cc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,q11c,q11cc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,q12c,q12cc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,q22c,q22cc,ifltr)
    
    b11 = 2.0*delta**2*(q11cc - alpha**2*np.abs(dacc)*d11cc)
    b21 = 2.0*delta**2*(q12cc - alpha**2*np.abs(dacc)*d12cc)
    b31 = 2.0*delta**2*(q22cc - alpha**2*np.abs(dacc)*d22cc)
    
    # Leith
    h11c = Wc*d11c
    h12c = Wc*d12c
    h22c = Wc*d22c
    
    all_filter(nxc,nyc,nxcc,nycc,Wc,Wcc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,h11c,h11cc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,h12c,h12cc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,h22c,h22cc,ifltr)
    
    b12 = 2.0*delta**3*(h11cc - alpha**3*np.abs(Wcc)*d11cc)
    b22 = 2.0*delta**3*(h12cc - alpha**3*np.abs(Wcc)*d12cc)
    b32 = 2.0*delta**3*(h22cc - alpha**3*np.abs(Wcc)*d22cc)
    
    # Horiuti
    all_filter(nxc,nyc,nxcc,nycc,a11c,a11cc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,a12c,a12cc,ifltr)
    all_filter(nxc,nyc,nxcc,nycc,a22c,a22cc,ifltr)
    
    p11cc = 0.5*(uccy+vccx)*(vccx-uccy)
    p12cc = 0.5*(vccy-uccx)*(vccx-uccy)
    p22cc = -0.5*(uccy+vccx)*(vccx-uccy)
    
    b13 = 2.0*delta**2*(a11cc - alpha**2*p11cc)
    b23 = 2.0*delta**2*(a12cc - alpha**2*p12cc)
    b33 = 2.0*delta**2*(a22cc - alpha**2*p22cc)   
    
    # Deviotoric L
    l11 = uucc - ucc*ucc
    l12 = uvcc - ucc*vcc
    l22 = vvcc - vcc*vcc
    
    l1 = l11 - 0.5*(l11 + l22)
    l2 = l12
    l3 = l12 - 0.5*(l11 + l22)
   
    if ics == 1:
        CS2 = (-b12*b23*l3 + b12*b33*l2 + b13*b22*l3 - b13*b32*l2 - b22*b33*l1 + b23*b32*l1)/ \
              (-b11*b22*b33 + b11*b23*b32 + b12*b21*b33 - b12*b23*b31 - b13*b21*b32 + b13*b22*b31)
        
        CL3 = (b11*b23*l3 - b11*b33*l2 - b13*b21*l3 + b13*b31*l2 + b21*b33*l1 - b23*b31*l1)/ \
              (-b11*b22*b33 + b11*b23*b32 + b12*b21*b33 - b12*b23*b31 - b13*b21*b32 + b13*b22*b31)
              
        CH2 = (-b11*b22*l3 + b11*b32*l2 + b12*b21*l3 - b12*b31*l2 - b21*b32*l1 + b22*b31*l1)/\
              (-b11*b22*b33 + b11*b23*b32 + b12*b21*b33 - b12*b23*b31 - b13*b21*b32 + b13*b22*b31)  
              
    elif ics == 2:
        CS2 = 0.04
        CL3 = 0.008
        CH2 = 0.04 # constant
    
    return CS2, CL3, CH2
                          
#%%
def compute_stress_hybrid(nx,ny,nxc,nyc,dxc,dyc,u,v,n,ist,ics,ifltr,alpha):
    
    '''
    compute the true stresses and Smagorinsky stresses
    
    Inputs
    ------
    nx,ny : number of grid points in x and y direction on fine grid
    nxc,nyc : number of grid points in x and y direction on coarse grid
    dxc,dyc : grid spacing in x and y direction    
    u : x-direction velocity on fine grid
    v : y-direction velocity on fine grid
    n : time-step
    
    Output
    ------
    uc, vc, uuc, uvc, vvc, t, ts
    '''
    
    uc = np.empty((nxc+1,nyc+1))
    vc = np.empty((nxc+1,nyc+1))
    t11 = np.empty((nxc+1,nyc+3))
    t12 = np.empty((nxc+1,nyc+1))
    t22 = np.empty((nxc+1,nyc+1))
    t11_s = np.empty((nxc+1,nyc+1))
    t12_s = np.empty((nxc+1,nyc+1))
    t22_s = np.empty((nxc+1,nyc+1))
    t = np.empty((3,nxc+1,nyc+1)) # true shear stress
    t_s = np.empty((3,nxc+1,nyc+1)) # Smagorinsky shear stress
    
    uu = np.empty((nx+1,ny+1))
    uv = np.empty((nx+1,ny+1))
    vv = np.empty((nx+1,ny+1))
    uuc = np.empty((nxc+1,nyc+1))
    uvc = np.empty((nxc+1,nyc+1))
    vvc = np.empty((nxc+1,nyc+1))
    
    ux = np.empty((nxc+1,nyc+1))
    uy = np.empty((nxc+1,nyc+1))
    vx = np.empty((nxc+1,nyc+1))
    vy = np.empty((nxc+1,nyc+1))
   
    uu = u*u
    uv = u*v
    vv = v*v
    
    coarsen(nx,ny,nxc,nyc,u,uc)
    coarsen(nx,ny,nxc,nyc,v,vc)
    coarsen(nx,ny,nxc,nyc,uu,uuc)
    coarsen(nx,ny,nxc,nyc,uv,uvc)
    coarsen(nx,ny,nxc,nyc,vv,vvc)
    
    #True (deviatoric stress)
    t11 = uuc -uc*uc
    t12 = uvc -uc*vc
    t22 = vvc -vc*vc
    
    t11d = t11 - 0.5*(t11+t22)
    t22d = t22 - 0.5*(t11+t22)
    
    t[0,:,:] = t11d
    t[1,:,:] = t12
    t[2,:,:] = t22d

    delta = np.sqrt(dxc*dyc)
    
    ux,uy = grad_spectral(nxc,nyc,uc)
    vx,vy = grad_spectral(nxc,nyc,vc)
    
    # parameters for Smagorinsky model
    d11 = ux
    d12 = 0.5*(uy+vx)
    d22 = vy
    da = np.sqrt(2.0*ux*ux + 2.0*vy*vy + (uy+vx)*(uy+vx)) # |S|
    
    # parameters for Leith model
    wc = vx - uy
    wcx,wcy = grad_spectral(nxc,nyc,wc)
    W = np.sqrt(wcx*wcx + wcy*wcy)  # |W|
    
    # parameters of Horiuti model
    a11 = 0.5*(uy+vx)*(vx-uy)
    a12 = 0.5*(vy-ux)*(vx-uy)
    a22 = -0.5*(uy+vx)*(vx-uy)
       
    CS2,CL3,CH2 = compute_cs_hybrid(dxc,dyc,nxc,nyc,uc,vc,da,d11,d12,d22,W,
                                    a11,a12,a22,ics,ifltr,alpha) # for Smagorinsky
    
    print(n, " CS = ", np.sqrt(np.max(CS2)), " ", np.sqrt(np.abs(np.min(CS2))),
          " CL = ", (np.abs(np.max(CL3)))**(1/3), " ", (np.abs(np.min(CL3)))**(1/3),
          " CH = ", (np.abs(np.max(CH2)))**(1/2), " ", (np.abs(np.min(CH2)))**(1/2))
    
    
    t11_s = -2.0*CS2*delta**2*da*d11 - 2.0*CL3*delta**3*W*d11 - 2.0*CH2*delta**2*a11
    t12_s = -2.0*CS2*delta**2*da*d12 - 2.0*CL3*delta**3*W*d12 - 2.0*CH2*delta**2*a12
    t22_s = -2.0*CS2*delta**2*da*d22 - 2.0*CL3*delta**3*W*d22 - 2.0*CH2*delta**2*a22
    
    t_s[0,:,:] = t11_s
    t_s[1,:,:] = t12_s
    t_s[2,:,:] = t22_s
                              
#%%                          
def compute_stress(nx,ny,nxc,nyc,dxc,dyc,u,v,n,ist,ics,ifltr,ihr,alpha):
    if ist == 1 or ist == 5:
        compute_stress_smag(nx,ny,nxc,nyc,dxc,dyc,u,v,n,ist,ics,ifltr,alpha)
    elif ist == 2:
        compute_stress_leith(nx,ny,nxc,nyc,dxc,dyc,u,v,n,ist,ics,ifltr,alpha)
    elif ist == 3:
        compute_stress_horiuti(nx,ny,nxc,nyc,dxc,dyc,u,v,n,ist,ics,ifltr,ihr,alpha)
    elif ist == 4:
        compute_stress_hybrid(nx,ny,nxc,nyc,dxc,dyc,u,v,n,ist,ics,ifltr,alpha)
    
#%% 
# read input file
l1 = []
with open('input_aprior.txt') as f:
    for l in f:
        l1.append((l.strip()).split("\t"))

nd = np.int64(l1[0][0])
nt = np.int64(l1[1][0])
re = np.float64(l1[2][0])
dt = np.float64(l1[3][0])
ns = np.int64(l1[4][0])
isolver = np.int64(l1[5][0])
isc = np.int64(l1[6][0])
ich = np.int64(l1[7][0])
ipr = np.int64(l1[8][0])
ndc = np.int64(l1[9][0])
alpha = np.float64(l1[10][0])

freq = int(nt/ns)

if (ich != 19):
    print("Check input.txt file")

#%%
ist = 1         # 1: Smagoronsky, 2: Leith, 3: Horiuti, 4: Hybrid, 5: Bardina
ics = 1         # 1: Germano (dynamic), 2: static
ifltr = 1       # 1: ideal (LES), 2: Trapezoidal, 3: Gaussian, 4: Elliptic
ihr = 3         # 1: model-1, 2: model-2, 3: model-3

#%% 
# assign parameters
nx = nd
ny = nd

nxc = ndc
nyc = ndc

pi = np.pi
lx = 2.0*pi
ly = 2.0*pi

dx = lx/np.float64(nx)
dy = ly/np.float64(ny)

dxc = lx/np.float64(nxc)
dyc = ly/np.float64(nyc)
    
#%%
for n in range(1,ns+1):
    folder = "data_"+str(nx)
    file_input = "../data_spectral/"+folder+"/05_streamfunction/s_"+str(n)+".csv"
    s = np.genfromtxt(file_input, delimiter=',')
    file_input = "../data_spectral/"+folder+"/04_vorticity/w_"+str(n)+".csv"
    w = np.genfromtxt(file_input, delimiter=',') 
    
    wc = coarsen(nx,ny,nxc,nyc,w)
    sc = coarsen(nx,ny,nxc,nyc,s)
    
    folder = "data_" + str(nx) + "_" + str(nxc) 
    if not os.path.exists("../data_spectral/"+folder+"/00_wc"):
        os.makedirs("../data_spectral/"+folder+"/00_wc")
        os.makedirs("../data_spectral/"+folder+"/00_sc")
        os.makedirs("../data_spectral/"+folder+"/u")
        os.makedirs("../data_spectral/"+folder+"/v")
    
    filename = "../data_spectral/"+folder+"/00_wc/wc_"+str(int(n))+".csv"
    np.savetxt(filename, wc, delimiter=",")
    filename = "../data_spectral/"+folder+"/00_sc/sc_"+str(int(n))+".csv"
    np.savetxt(filename, sc, delimiter=",")
    
    #u,v = compute_velocity(nx,ny,dx,dy,s)
    sx,sy = grad_spectral(nx,ny,s)
    u = sy
    v = -sx
    filename = "../data_spectral/"+folder+"/u/u_"+str(int(n))+".csv"
    np.savetxt(filename, u, delimiter=",")
    filename = "../data_spectral/"+folder+"/v/v_"+str(int(n))+".csv"
    np.savetxt(filename, v, delimiter=",")
        
    compute_stress(nx,ny,nxc,nyc,dxc,dyc,u,v,n,ist,ics,ifltr,ihr,alpha)


#%%
folder = "data_" + str(nx) + "_" + str(nxc) 
tt = np.genfromtxt("../data_spectral/"+folder+"/true_shear_stress/t_"+str(ns)+".csv", delimiter=',') 
tt = tt.reshape((3,nxc+1,nyc+1))
t11t = tt[0,:,:]
t12t = tt[1,:,:]
t22t = tt[2,:,:]

ts = np.genfromtxt("../data_spectral/"+folder+"/smag_shear_stress/ts_"+str(ns)+".csv", delimiter=',') 
ts = ts.reshape((3,nxc+1,nyc+1))
t11sm_s = ts[0,:,:]
t12sm_s = ts[1,:,:]
t22sm_s = ts[2,:,:]

num_bins = 64

fig, axs = plt.subplots(1,3,figsize=(12,4))
axs[0].set_yscale('log')
axs[1].set_yscale('log')
axs[2].set_yscale('log')

# the histogram of the data
ntrue, binst, patchest = axs[0].hist(t11t.flatten(), num_bins, histtype='step', alpha=1, color='r',zorder=5,
                                 linewidth=2.0,range=(-4*np.std(t11t),4*np.std(t11t)),density=True,
                                 label="True")
ntrue, binst, patchest = axs[0].hist(t11sm_s.flatten(), num_bins, histtype='step', alpha=1, color='b',zorder=5,
                                 linewidth=2.0,range=(-4*np.std(t11t),4*np.std(t11t)),density=True,
                                 label="Static")


ntrue, binst, patchest = axs[1].hist(t12t.flatten(), num_bins, histtype='step', alpha=1, color='r',zorder=5,
                                 linewidth=2.0,range=(-4*np.std(t12t),4*np.std(t12t)),density=True,
                                 label="True")
ntrue, binst, patchest = axs[1].hist(t12sm_s.flatten(), num_bins, histtype='step', alpha=1, color='b',zorder=5,
                                 linewidth=2.0,range=(-4*np.std(t12t),4*np.std(t12t)),density=True,
                                 label="Static")

ntrue, binst, patchest = axs[2].hist(t22t.flatten(), num_bins, histtype='step', alpha=1, color='r',zorder=5,
                                 linewidth=2.0,range=(-4*np.std(t22t),4*np.std(t22t)),density=True,
                                 label="True")
ntrue, binst, patchest = axs[2].hist(t22sm_s.flatten(), num_bins, histtype='step', alpha=1, color='b',zorder=5,
                                 linewidth=2.0,range=(-4*np.std(t22t),4*np.std(t22t)),density=True,
                                 label="Static")

x_ticks = np.arange(-4*np.std(t11t), 4.1*np.std(t11t), np.std(t11t))                                  
x_labels = [r"${} \sigma$".format(i) for i in range(-4,5)]

axs[0].set_title(r"$\tau_{11}^d$")
#axs[0].set_xticks(x_ticks)                              

axs[1].set_title(r"$\tau_{12}^d$")

axs[2].set_title(r"$\tau_{22}^d$")

# Tweak spacing to prevent clipping of ylabel
axs[0].legend()            
axs[1].legend()   
axs[2].legend()   

fig.tight_layout()
plt.show()


#%%
#x = np.linspace(0,2.0*np.pi,65)
#y = np.linspace(0,2.0*np.pi,65)
#X, Y = np.meshgrid(x,y)
#x = x.reshape(1,65)
#y = y.reshape(65,1)
#z = np.sin(X) + np.sin(Y)
#Z = np.sin(x) + np.sin(y)
#plt.contourf(z)
#Zx = np.cos(X)
#Zy = np.cos(Y)
#zx, zy  = grad_spectral(64,64,z)
