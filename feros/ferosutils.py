import pyfits
import numpy as np
from numpy import median,sqrt,array,exp
import scipy
from scipy import signal,special,optimize,interpolate
import scipy.special as sp
import copy
import glob
import os
from pylab import *
import sys
base = '../'
sys.path.append(base+"utils/BaryCor")
import BaryCor

from rpy2 import robjects
import rpy2.robjects.numpy2ri

####### agregado por mi ####
#import rpy2.robjects.numpy2ri
#rpy2.robjects.numpy2ri.activate()
############################
r = robjects.r
#r.library("MASS")

def gauss2(params,x):
	amp1 = params[0]
	amp2 = params[1]
	med1 = params[2]
	med2 = params[3]
	sig1 = params[4]
	sig2 = params[5]
	g1 = amp1 * np.exp(-0.5*((x-med1)/sig1)**2)
        g2 = amp2 * np.exp(-0.5*((x-med2)/sig2)**2)
	return g1 + g2

def res_gauss2(params,g,x):
	return g-gauss2(params,x)

def get_RG(h):
	if h['HIERARCH ESO DET READ MODE'] == 'normal':
		ron = 5.1
		gain = 3.2
	elif h['HIERARCH ESO DET READ MODE'] == 'slow':
		ron = 3.0
		gain = 1.0
	else:
		ron = 7.2
		gain = 2.7
	return ron,gain

def MedianCombine(ImgList, zero_bo=False, zero='MasterBias.fits'):
    """
    Median combine a list of images
    """
    if zero_bo:
    	BIAS = pyfits.getdata(zero)

    n = len(ImgList)
    if n==0:
        raise ValueError("empty list provided!")

    h = pyfits.open(ImgList[0])[0]
    d = h.data
    d = OverscanTrim(d)
    d = b_col(d)
    if zero_bo:
	d -= BIAS
    d = np.round(d).astype('int')

    factor = 1.25
    if (n < 3):
        factor = 1

    #ronoise = factor * h.header['HIERARCH ESO CORA CCD RON'] / np.sqrt(n)
    #gain    = h.header['HIERARCH ESO CORA CCD GAIN']
    ronoise, gain = get_RG(h.header)
    ronoise = ronoise/np.sqrt(n)

    if (n == 1):
        return d, ronoise, gain
    else:
        for i in range(n-1):
            #print i   
            h = pyfits.open(ImgList[i+1])[0]
            ot = OverscanTrim(h.data)
	    ot = b_col(ot)
	    if zero_bo:
            	d = np.dstack((d,np.round((ot - BIAS)).astype('int')))
	    else:
		d = np.dstack((d,np.round(ot).astype('int')))
        return np.median(d,axis=2), ronoise, gain

def OverscanTrim(d):
    """
    Overscan correct and Trim a refurbished FEROS image
    """
    ps = d[:,:48]
    os = d[:,-48:]
    s = 0.5*(np.median(ps,axis=1)+np.median(os,axis=1))
    c = np.polyfit(np.arange(len(s)),s,4)
    overscan = np.polyval(c,np.arange(len(s)))
    newdata = np.zeros(d[:,50:-50].shape)
    for i in range(len(overscan)):
        newdata[i,:] = d[i,50:-50] - overscan[i]
    return newdata

def b_col(d):
	
	d2 = np.zeros(d.shape)
	ps = [[1675.,4097., 219.],\
	      [1675.,1780., 222.],\
	      [   0.,4097., 320.],\
	      [   0.,4097., 326.],\
	      [1616.,1617., 334.],\
	      [1617.,1641., 334.],\
	      [1641.,1696., 335.],\
	      [1696.,4097., 335.],\
	      [1617.,1641., 338.],\
	      [1622.,1741., 342.],\
	      [1622.,1741., 343.],\
	      [ 868.,4097., 646.],\
	      [1514.,2101., 843.],\
	      [1501.,1691., 857.],\
	      [1501.,1691., 858.],\
	      [1475.,1681., 883.],\
	      [1459.,4097., 900.],\
	      [1454.,1501., 916.],\
              [1404.,4907.,1062.],\
	      [1404.,4907.,1063.],\
	      [1404.,4907.,1064.],\
	      [ 608.,4097.,1298.],\
	      [   0., 608.,1299.],\
	      [ 608.,4097.,1299.]]
	
	for i in range(len(ps)):
		d2[ps[i][0]:ps[i][1],ps[i][2]] = 1
	ej = np.arange(d.shape[1])
	for i in range(d.shape[0]):
		vec = d[i]
		I = np.where(d2[i]==0)[0]
		I2 = np.where(d2[i]==1)[0]
		if len(I2)>0:
			tck = scipy.interpolate.splrep(ej[I],vec[I],k=1)
			d[i] = scipy.interpolate.splev(ej,tck)

	return d

def gauss(params,x):
	med = params[0]
	sig = params[1]
	g = np.exp(-0.5*(x-med)*(x-med)/(sig*sig))
	return g

def res_gauss(params,g,x):
	return g-gauss(params,x)

def FileClassify(diri, log):
    """
    Classifies all files in a directory and writes a night log of science images
    """

    # define output lists
    simThAr_sci = []
    simSky_sci  = []
    biases      = []
    bias_dates  = []
    flat_dates  = []
    flats       = []
    ThArNe_ref  = []
    ThAr_Ne_ref = []
    ThArNe_ref_dates  = []
    ThAr_Ne_ref_dates = []

    f = open(log,'w')
    bad_files = []
    if os.access(diri+'bad_files.txt',os.F_OK):
    	bf = open(diri+'bad_files.txt')
	linesbf = bf.readlines()
	for line in linesbf:
		bad_files.append(diri+line[:-1])
	bf.close()
    
    all_files = glob.glob(diri+"*fits")
    
    jj = 0
    for archivo in all_files:
	jj+=1
	dump = False
	for bf in bad_files:
		if archivo == bf:
			dump = True
			break
	
	if not dump:
		h = pyfits.open(archivo)
		print archivo, h[0].header['HIERARCH ESO DPR TYPE']
		if True:
			if h[0].header['HIERARCH ESO DPR TYPE'] == 'OBJECT,WAVE' or h[0].header['HIERARCH ESO DPR TYPE'] == 'VELOC,WAVE':
				
		    		simThAr_sci.append(archivo)
		    		obname = h[0].header['OBJECT']
		    		ra     = h[0].header['HIERARCH ESO INS ADC1 RA']
		    		delta  = h[0].header['HIERARCH ESO INS ADC1 DEC']
				try:
		    			airmass= h[0].header['HIERARCH ESO TEL AIRM START']
				except:
					airmass = -999.
		    		texp   = h[0].header['EXPTIME']
		    		date   = h[0].header['DATE-OBS']
		    		line = "%-15s %10s %10s %8.2f %4.2f %s %8s %s\n" % (obname, ra, delta, texp, airmass, h[0].header['HIERARCH ESO DPR TYPE'], date, archivo)
		    		f.write(line)
			elif h[0].header['HIERARCH ESO DPR TYPE'] == 'OBJECT,SKY' or h[0].header['HIERARCH ESO DPR TYPE'] == 'VELOC,SKY':
		 		simSky_sci.append(archivo)
		    		obname = h[0].header['OBJECT']
		    		ra     = h[0].header['HIERARCH ESO INS ADC1 RA']
		    		delta  = h[0].header['HIERARCH ESO INS ADC1 DEC']
				try:
		    			airmass= h[0].header['HIERARCH ESO TEL AIRM START']
				except:
					airmass = -999.
		    		texp   = h[0].header['EXPTIME']
		    		date   = h[0].header['DATE-OBS']
		    		line = "%-15s %10s %10s %8.2f %4.2f %s %8s %s\n" % (obname, ra, delta, texp, airmass, h[0].header['HIERARCH ESO DPR TYPE'], date, archivo)
		    		f.write(line)

			elif h[0].header['HIERARCH ESO DPR TYPE'] == 'BIAS':
			    biases.append(archivo)
			    mjd,mjd0 = mjd_fromheader(h)
			    bias_dates.append(mjd)

			elif h[0].header['HIERARCH ESO DPR TYPE'] == 'FLAT':
			    flats.append(archivo)
			    mjd,mjd0 = mjd_fromheader(h)
			    flat_dates.append(mjd)

			elif h[0].header['HIERARCH ESO DPR TYPE'] == 'WAVE':
			    div = archivo.split('_')
			    if h[0].header['HIERARCH ESO INS CALMIRR2 ID'] == 'LAMP1':
				ThArNe_ref.append(archivo)
			    	mjd, mjd0 = mjd_fromheader(h)
			    	ThArNe_ref_dates.append( mjd )
			    elif h[0].header['HIERARCH ESO INS CALMIRR2 ID'] == 'LAMP3':
				ThAr_Ne_ref.append(archivo)
		    		mjd, mjd0 = mjd_fromheader(h)
		    		ThAr_Ne_ref_dates.append( mjd )

		# now build log
		# retrieve object name
       
    f.close()
    biases, bias_dates = np.array(biases), np.array(bias_dates)
    flats, flat_dates  = np.array(flats), np.array(flat_dates)
    IS = np.argsort(bias_dates)
    biases, bias_dates = biases[IS], bias_dates[IS]
    IS = np.argsort(flat_dates)
    flats, flat_dates = flats[IS], flat_dates[IS]   

    return biases, flats, ThArNe_ref, ThAr_Ne_ref, simThAr_sci, simSky_sci, ThArNe_ref_dates, ThAr_Ne_ref_dates

def mjd_fromheader(h):
    """
    return modified Julian date from header
    """
    
    datetu = h[0].header['DATE-OBS']
    if len(datetu) < 23:
	mjd_start = h[0].header['MJD-OBS']
	mjd0 = 2400000.5
    else:
	    #print datetu
	    mjd0,mjd,i = BaryCor.iau_cal2jd(int(datetu[:4]),int(datetu[5:7]),int(datetu[8:10]))
	    ho = int(datetu[11:13])
	    mi = int(datetu[14:16])
	    se = float(datetu[17:])
	    ut = float(ho) + float(mi)/60.0 + float(se)/3600.0
	    mjd_start = mjd + ut/24.0

    secinday = 24*3600.0
    fraction = 0.5
    texp     = h[0].header['EXPTIME'] #sec

    mjd = mjd_start + (fraction * texp) / secinday

    return mjd, mjd0
		
def Lines_mBack(thar, sd,  thres_rel=3, pl=False):
    """ 
    Given an extracted ThAr order, return a version where the background has been removed
    """


    L = np.where(sd > 0)

    # initial background estimate, simple 25% percentile on a 100-pixel filter
    bkg = np.zeros( len(sd) )
    bkg[L] = scipy.signal.order_filter(thar[L],np.ones(101),25)
    d = thar - bkg

    lines = FindLines_simple_sigma(d,sd, thres=thres_rel)
    # Now, mask these lines
    mask = np.ones( len(sd) )
        
    for kk in lines:
        #mask region
        if (d[kk] > 10000):
            mask[kk-3:kk+4] = 0
        elif (d[kk] > 5000):
            mask[kk-3:kk+4] = 0
        elif (d[kk] > 1000):
            mask[kk-3:kk+4] = 0
        else:
            mask[kk-3:kk+4] = 0
    
    # New, final background estimnate
    X = np.array( range( len( d ) ) )
    K = np.where((sd > 0) & (mask > 0))

    bkg = np.zeros( len(sd) )
    bkg_T = np.array( r.lowess(X[K], thar[K].astype('double'),  f=0.2, iter=3) )

    # interpolate linearly to all of X
    Temp = np.array( r.approx(bkg_T[0],bkg_T[1],xout=X[L], method="linear", rule=2) )
    bkg[L] = Temp[1]

    return bkg

def Wav_Solution_vel_shift(p_ref, pix_centers, wavelengths, minlines=80, maxrms=20, Cheby=False, Inv = False, l=4096,b=1):

    def fitfunc(p, p_ref,x, m):
	ret = (1+1e-6*p) * scipy.polyval(p_ref,x)    
        return ret
    errfunc = lambda p,p_ref,x,y: np.ravel( (fitfunc(p,p_ref,x)-y) )
 
    def fitfunc_cheb(p,p_ref,x):
        ret = (1+1e-6*p) * Cheby_eval (p_ref,x,l,b)
        return ret
    errfunc_cheb_nw = lambda p,p_ref,x,y: np.ravel( (fitfunc_cheb(p,p_ref,x)-y) )

        
    p0 = np.array( [0] )

    if (Cheby):
        p1, success =  scipy.optimize.leastsq(errfunc_cheb_nw, p0, args=(p_ref,pix_centers, wavelengths ))
        residuals   =  errfunc_cheb_nw(p1, p_ref, pix_centers, wavelengths)
    else:
        p1, success = scipy.optimize.leastsq(errfunc, p0, args=(p_ref, pix_centers, wavelengths))
        residuals    = errfunc(p1, p_ref, pix_centers, wavelengths)

    residuals_ms = 299792458.0 * residuals / wavelengths
    rms_ms       = np.sqrt( np.var( residuals_ms ) ) 

    N_l = len( pix_centers )
    I = range( N_l )

    cond = 1
    L = np.where( abs(residuals_ms) > 3.0*rms_ms )
    if ( (len(L[0]) == 0) and (rms_ms < maxrms) ) or (N_l < minlines): 
        cond=0
    
    #print "Start Global culling with ", N_l, " number of lines"
    while (cond):        
        index_worst = np.argmax( abs(residuals) )
	wavelengths = np.delete(wavelengths,index_worst)
	pix_centers = np.delete(pix_centers,index_worst)
        N_l -= 1
        if (Cheby):
            p1, success =  scipy.optimize.leastsq(errfunc_cheb_nw, p0, args=(p_ref,pix_centers, wavelengths ))
	    residuals   =  errfunc_cheb_nw(p1, p_ref, pix_centers, wavelengths)
        else:
           p1, success = scipy.optimize.leastsq(errfunc, p0, args=(p_ref, pix_centers, wavelengths))
	   residuals    = errfunc(p1, p_ref, pix_centers, wavelengths)

        residuals_ms = 299792458.0 * residuals / wavelengths
        rms_ms       = np.sqrt( np.var( residuals_ms ) ) 
        #print 'p1',(1e-6*p1)*299792458.0, rms_ms 
        L = np.where( abs(residuals_ms) > 3.*rms_ms )
        if ( (len(L[0]) == 0) and (rms_ms < maxrms) ) or (N_l < minlines): 
            cond=0

    #print "Final RMS is ", rms_ms
    #print "Number of lines is ", N_l
    #print "--> Achievable RV precision is ", rms_ms/np.sqrt(N_l)
    #print p1
    #print "Velocity of ThAr w/r to solution provided is ", (1e-6*p1)*299792458.0

    return p1, pix_centers, wavelengths, rms_ms, residuals 

def FindLines_simple_sigma(d,sd,thres=3):
    """
    Given an array, find lines above a sigma-threshold
    """
    L = np.where( (d > (thres*sd)) & (d > 0) )  
    lines = []
    for i in range(np.shape(L)[1]):
        j = L[0][i]
        if ((d[j] > d[j-1]) & (d[j-1] > d[j-2]) & (d[j] > d[j+1]) & (d[j+1] > d[j+2])):
            lines.append(j)
    
    return lines

def Cheby_eval(p,x,l,b=1):
    """
    evaluates Chebyshev polynomial fit at x given best-fit parameters p
    """
    med = int( float( float(l) / float(b) ))
    x_norm = (x-med) / med
    order = len(p) - 1
    ret_val = 0.0
    for i in range(order + 1):
        ret_val += p[order - i]*scipy.special.chebyt(i)(x_norm)
    
    return ret_val
### wavelength calibration routines ###
def sigma_clip(vec,lim=3.0):
	while True:
		med = np.median(vec)
		res = vec - med
		rms = np.sqrt(np.var(res))
		I   = np.where(np.absolute(res) < lim*rms)[0]
		if len(I) == len(vec):
			break
		else:
			vec = vec[I]
	return vec

