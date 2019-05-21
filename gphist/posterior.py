"""Expansion history posterior applied to distance functions.
"""

import math
from abc import ABCMeta,abstractmethod

import numpy as np
import numpy.linalg
import astropy.constants

class GaussianPdf(object):
	"""Represents a multi-dimensional Gaussian probability density function.

	Args:
		mean(ndarray): 1D array of length npar of mean values.
		covariance(ndarray): 2D symmetric positive definite covariance matrix
			of shape (npar,npar).

	Raises:
		ValueError: dimensions of mean and covariance are incompatible.
		LinAlgError: covariance matrix is not positive definite.
	"""
	def __init__(self,mean,covariance):
		# Check that the dimensions match or throw a ValueError.
		#dimensions_check = mean.dot(covariance.dot(mean))
		# Check that the covariance is postive definite or throw a LinAlgError.
        #posdef_check = numpy.linalg.cholesky(covariance[:,:,0])

		self.mean = mean
		'''
		if len(covariance.shape) > 2: #this assumes there are exactly 3 covariance matrices for 3 redshifts.  This should no longer happen
			temp_icov = np.linalg.inv(covariance[:,:,0])
			for i in range(1,covariance.shape[2]):
			    stack_temp = np.linalg.inv(covariance[:,:,i])
			    temp_icov = np.dstack([temp_icov,stack_temp])
			self.icov = temp_icov
			temp_norm = 0.5*mean.size*np.log(2*math.pi) + 0.5*(np.log(np.linalg.det(covariance[:,:,0])))
			for i in range(1,covariance.shape[2]):
			    temp_norm+=0.5*(np.log(np.linalg.det(covariance[:,:,i])))
			self.norm = temp_norm
		else:
		'''
		self.icov = np.linalg.inv(covariance)
		self.norm = 0.5*mean.size*np.log(2*math.pi) + 0.5*np.log(np.linalg.det(covariance))
		# Calculate the constant offset of -log(prob) due to the normalization factors.

	def get_nlp(self,values):
		"""Calculates -log(prob) for the PDF evaluated at specified values.

		The calculation is automatically broadcast over multiple value vectors.

		Args:
			values(ndarray): Array of values where the PDF should be evaluated with
				shape (neval,ndim) where ndim is the dimensionality of the PDF and
				neval is the number of points where the PDF should be evaluated.
			more precisely, it has shape (nsamples,ntype,nzposterior)
			nsamples is the number of samples requested
			ntype is the number of types of posteriors, types being DH, DA or mu
			nzposterior is the number of redshifts in a given posterior

		Returns:
			float: Array of length neval -log(prob) values calculated at each input point.

		Raises:
			ValueError: Values can not be broadcast together with our mean vector.
		"""
		# The next line will throw a ValueError if values cannot be broadcast.
		residuals = values - self.mean
		chisq = np.einsum('...ij,jk,...ik->...i',residuals,self.icov,residuals)

		print('chi sq is ')
		print(chisq.min(),np.sqrt(np.var(chisq)))
		print(self.norm)
		return self.norm + 0.5*chisq

class GaussianPdf1D(GaussianPdf):
	"""Represents a specialization of GaussianPdf to the 1D case.

	Args:
		central_value(float): Central value of the 1D PDF.
		sigma(float): RMS spread of the 1D PDF.
	"""
	def __init__(self,central_value,sigma):
		# the np.arrays are for turning floats to arrays which have shape attributes
		mean = np.array([central_value])
		covariance = np.array([[sigma**2]])
		GaussianPdf.__init__(self,mean,covariance)

	def get_nlp(self,values):
		"""Calculates -log(prob) for the PDF evaluated at specified values.

		Args:
			values(ndarray): Array of values where the PDF should be evaluated with
				length neval.

		Returns:
			float: Array of length neval -log(prob) values calculated at each input point.
		"""
		#return GaussianPdf.get_nlp(self,values[:,np.newaxis])
		return GaussianPdf.get_nlp(self,values)

class GaussianPdf2D(GaussianPdf):
	"""Represents a specialization of GaussianPdf to the 2D case.

	Args:
		x1(float): Central value of the first parameter.
		x2(float): Central value of the second parameter.
		sigma1(float): RMS spread of the first parameter.
		sigma2(float): RMS spread of the second parameter.
		rho12(float): Correlation coefficient between the two parameters. Must be
			between -1 and +1.
	"""
	def __init__(self,x1,sigma1,x2,sigma2,rho12):
		mean = np.array([x1,x2])
		cov12 = sigma1*sigma2*rho12
		covariance = np.array([[sigma1**2,cov12],[cov12,sigma2**2]])
		GaussianPdf.__init__(self,mean,covariance)

class Posterior(object):
	"""Posterior constraint on DH,DA at a fixed redshift.

	This is an abstract base class and subclasses must implement the constraint method.

	Args:
		name(str): Name to associate with this posterior.
		zpost(float): Redshift of posterior constraint.
	"""
	__metaclass__ = ABCMeta
	def __init__(self,name,zpost):
		self.name = name
		self.zpost = zpost

	@abstractmethod
	def constraint(self,DHz,DAz,muz):
		"""Evaluate the posterior constraint given values of DH(zpost) and DA(zpost).

		Args:
			DHz(ndarray): Array of DH(zpost) values.
			DAz(ndarray): Array of DA(zpost) values with the same shape as DHz.
			muz(ndarray): this is no longer the 5log(DL/10pc) but instead 5 log (DL/DH0)

		Returns:
			nlp(ndarray): Array of -log(prob) values with the same shape as DHz and DAz.
		"""
		pass

	def get_nlp(self,zprior,DH,DA,mu):
		"""Calculate -log(prob) for the posterior applied to a set of expansion histories.

		The posterior is applied to c/H(z=0).

			zprior(ndarray): Redshifts where prior is sampled, in increasing order.
			DH(ndarray): Array of shape (nsamples,nz) of DH(z) values to use.
			DA(ndarray): Array of shape (nsamples,nz) of DA(z) values to use.

		Returns:
			ndarray: Array of -log(prob) values calculated at each input value.

		Raises:
			AssertionError: zpost is not in zprior.
		"""
		iprior = np.where(np.in1d(zprior,self.zpost))[0] #for whatever reason np.where returns a tuple of an array so thats why there is the [0] after
		DHz = DH[:,iprior]
		DAz = DA[:,iprior]
		muz = mu[:,iprior]# these should be of the form (nsample,nz)
		return self.constraint(DHz,DAz,muz)

class LocalH0Posterior(Posterior):
	"""Posterior constraint on the value of H0 determined from local measurements.

	Args:
		name(str): Name to associate with this posterior.
		H0(float): Central value of H(z=0).
		H0_error(float): RMS error on H(z=0).
	"""
	def __init__(self,name,H0,H0_error):
		self.pdf = GaussianPdf1D(H0,H0_error)
		Posterior.__init__(self,name,0.)

	def constraint(self,DHz,DAz,muz):
		"""Calculate -log(prob) for the posterior applied to a set of expansion histories.

		The posterior is applied to c/H(z=0).

			DHz(ndarray): Array of DH(z=0) values to use.
			DAz(ndarray): Array of DA(z=0) values to use (will be ignored).
			muz(ndarray): this is no longer the 5log(DL/10pc) but instead 5 log (DL/DH0)

		Returns:
			ndarray: Array of -log(prob) values calculated at each input value.
		"""
		clight_km_per_sec = astropy.constants.c.to('km/s').value
		return self.pdf.get_nlp(clight_km_per_sec/DHz)

class DHPosterior(Posterior):
	"""Posterior constraint on DH(z).

	Args:
		name(str): Name to associate with this posterior.
		zpost(float): Redshift of posterior constraint.
		DH(float): Central value of DH(z).
		DH_error(float): RMS error on DH(z).
	"""
	def __init__(self,name,zpost,DH,DH_error):
		self.pdf = GaussianPdf1D(DH,DH_error)
		Posterior.__init__(self,name,zpost)

	def constraint(self,DHz,DAz,muz):
		"""Calculate -log(prob) for the posterior applied to a set of expansion histories.

		Args:
			DHz(ndarray): Array of DH(zpost) values to use.
			DAz(ndarray): Array of DA(zpost) values to use (will be ignored).
			muz(ndarray): this is no longer the 5log(DL/10pc) but instead 5 log (DL/DH0)

		Returns:
			ndarray: Array of -log(prob) values calculated at each input value.
		"""
		return self.pdf.get_nlp(DHz)

class DAPosterior(Posterior):
	"""Posterior constraint on DA(z).

	Args:
		name(str): Name to associate with this posterior.
		zpost(float): Redshift of posterior constraint.
		DA(float): Central value of DA(z).
		DA_error(float): RMS error on DA(z).
	"""
	def __init__(self,name,zpost,DA,DA_error):
		self.pdf = GaussianPdf1D(DA,DA_error)
		Posterior.__init__(self,name,zpost)

	def constraint(self,DHz,DAz,muz):
		"""Calculate -log(prob) for the posterior applied to a set of expansion histories.

		Args:
			DHz(ndarray): Array of DH(zpost) values to use (will be ignored).
			DAz(ndarray): Array of DA(zpost) values to use.
			muz(ndarray): this is no longer the 5log(DL/10pc) but instead 5 log (DL/DH0)

		Returns:
			ndarray: Array of -log(prob) values calculated at each input value.
		"""
		return self.pdf.get_nlp(DAz)

class CMBPosterior(Posterior):
	"""Posterior constraint on DH(zref) and DA(zref) from CMB with zpost ~ z*.

	Args:
		name(str): Name to associate with this posterior.
		zpost(float): Redshift where posterior should be evaluated.
		DH(float): Value of DH(zref) at zref=evol.zvalues[-1].
		DA1pz(float): Value of DA(zref)/(1+zref) at zref=evol.zvalues[-1].
		cov11(float): Variance of DH(zref).
		cov12(float): Covariance of DH(zref) and DA(zref)/(1+zref).
		cov22(float): Variance of DA(zref)/(1+zref).
	"""
	def __init__(self,name,zpost,DH,DA1pz,cov11,cov12,cov22):
		mean = np.array([DH,DA1pz*(1+zpost)])
		cov12 *= (1+zpost)
		cov22 *= (1+zpost)**2
		covariance = np.array([[cov11,cov12],[cov12,cov22]])
		self.pdf = GaussianPdf(mean,covariance)
		Posterior.__init__(self,name,zpost)

	def constraint(self,DHz,DAz,muz):
		"""Calculate -log(prob) for the posterior applied to a set of expansion histories.

		Args:
			DHz(ndarray): Array of DH(zpost) values to use.
			DAz(ndarray): Array of DA(zpost) values to use.
			muz(ndarray): this is no longer the 5log(DL/10pc) but instead 5 log (DL/DH0)

		Returns:
			ndarray: Array of -log(prob) values calculated at each input value.
		"""
		values = np.hstack([DHz,DAz]) #trying for the shape (nsamples,ndata) ndata = either nz, ntype or nz*ntype
		#old#dstack since DH(A)z are of the form (nsamples,nz) and we want (nsamples,nz,ntype)
		return self.pdf.get_nlp(values)

class BAOPosterior(Posterior):
	"""Posterior constraint on the parallel and perpendicular scale factors from Lya BAO.

	Args:
		name(str): Name to associate with this posterior.
		zpost(double): Redshift where posterior should be evaluated.
		apar(double): Line-of-sight (parallel) scale factor measured using BAO.
		sigma_apar(double): RMS error on measured apar.
		aperp(double): Transverse (perpendicular) scale factor measured using BAO.
		sigma_aperp(double): RMS error on measured aperp.
		rho(double): Correlation coefficient between apar and aperp.
			Must be between -1 and +1.

	Raises:
		AssertionError: The redshift z is not an element of zprior.
	"""
	def __init__(self,name,zpost,apar,sigma_apar,aperp,sigma_aperp,rho,rsdrag):
		self.rsdrag = rsdrag
		self.pdf = GaussianPdf2D(apar,sigma_apar,aperp,sigma_aperp,rho)
		Posterior.__init__(self,name,zpost)

	def constraint(self,DHz,DAz,muz):
		"""Calculate -log(prob) for the posterior applied to a set of expansion histories.

		The posterior is applied simultaneously to DH(z)/rs(zd) and DA(z)/rs(zd).

		Args:
			DHz(ndarray): Array of DH(zpost) values to use.
			DAz(ndarray): Array of DA(zpost) values to use.
			muz(ndarray): this is no longer the 5log(DL/10pc) but instead 5 log (DL/DH0)

		Returns:
			ndarray: Array of -log(prob) values calculated at each input value.
		"""
		values = np.hstack([DHz,DAz])/self.rsdrag#see CMB posterior comments
		return self.pdf.get_nlp(values)



class BAOPosteriorVardrag(Posterior):
	"""Posterior constraint on the parallel and perpendicular scale factors from Lya BAO.

	Args:
		name(str): Name to associate with this posterior.
		zpost(double): Redshift where posterior should be evaluated.
		apar(double): Line-of-sight (parallel) scale factor measured using BAO.
		sigma_apar(double): RMS error on measured apar.
		aperp(double): Transverse (perpendicular) scale factor measured using BAO.
		sigma_aperp(double): RMS error on measured aperp.
		rho(double): Correlation coefficient between apar and aperp.
			Must be between -1 and +1.

	Raises:
		AssertionError: The redshift z is not an element of zprior.
	"""
	def __init__(self,name,zpost,apar,sigma_apar,aperp,sigma_aperp,rho,rsdrag):
		self.rsdrag = rsdrag
		self.pdf = GaussianPdf2D(apar,sigma_apar,aperp,sigma_aperp,rho)
		Posterior.__init__(self,name,zpost)

	def constraint(self,DHz,DAz,muz):
		"""Calculate -log(prob) for the posterior applied to a set of expansion histories.

		The posterior is applied simultaneously to DH(z)/rs(zd) and DA(z)/rs(zd).

		Args:
			DHz(ndarray): Array of DH(zpost) values to use.
			DAz(ndarray): Array of DA(zpost) values to use.
			muz(ndarray): this is no longer the 5log(DL/10pc) but instead 5 log (DL/DH0)

		Returns:
			ndarray: Array of -log(prob) values calculated at each input value.
		"""
		# this needs some fixing as these DHzs are evaluated at the redshifts for their posterior
		# so DH[-1] is not DH z*
		values = np.dstack([DHz,DAz])/(self.rsdrag * DHz[-1]/1.9273724E-01)#see CMB posterior comments
		return self.pdf.get_nlp(values)



class SNPosterior(Posterior):
	"""Posterior constraint on mu(z).

	Args:
		name(str): Name to associate with this posterior.
		zpost(float): Redshift of posterior constraint.
		mu(float): Central value of mu*(z): actually mu(z)-(M_1=19.05).
		mu_error(float): RMS error on mu(z).
	"""
	def __init__(self,name,zpost,mu,mu_error):
		self.pdf = GaussianPdf(mu,mu_error)
		Posterior.__init__(self,name,zpost)


	def constraint(self,DHz,DAz,muz):
		"""Calculate -log(prob) for the posterior applied to a set of expansion histories.

		Args:
			DHz(ndarray): Array of DH(zpost) values to use (will be ignored).
			DAz(ndarray): Array of DA(zpost) values to use (also ignored).
			muz(ndarray): this is no longer the 5log(DL/10pc) but instead 5 log (DL/DH0)

		Returns:
			ndarray: Array of -log(prob) values calculated at each input value.
		"""
		return self.pdf.get_nlp(muz)



class BOSS2018Posterior(Posterior):
    """Posterior constraint on DH, DA for LRGs, with ALAM covariance

    Args:
        name(str): Name to associate with this posterior.
        zpost(float): Redshift of posterior constraint.
        mean(float): data. len(6)
        cov(float): cavariance matrix. 6x6
        rsdrag(float): fiducial rsdrag.
    """
    def __init__(self,name,zpost,mean,cov,rsdrag):
        self.rsdrag = rsdrag
        self.pdf = GaussianPdf(mean,cov)
        Posterior.__init__(self,name,zpost)

    def constraint(self,DHz,DAz,muz):
        """Calculate -log(prob) for the posterior applied to a set of expansion histories.

        Args:
            DHz(ndarray): Array of DH(zpost) values to use.
            DAz(ndarray): Array of DA(zpost) values to use.
            muz(ndarray): this is no longer the 5log(DL/10pc) but instead 5 log (DL/DH0)

        Returns:
            ndarray: Array of -log(prob) values calculated at each input value.
        """
        rfid = 149.28
        Hz = 2.99792458e5 /DHz *self.rsdrag /rfid
        DMz = DAz *rfid /self.rsdrag
        values = np.hstack([DMz,Hz])
        return self.pdf.get_nlp(values)



class BOSS2018PosteriorVardrag(Posterior):
    """Posterior constraint on DH, DA for LRGs, with ALAM covariance

    Args:
        name(str): Name to associate with this posterior.
        zpost(float): Redshift of posterior constraint.
        mean(float): data. len(6)
        cov(float): cavariance matrix. 6x6
        rsdrag(float): fiducial rsdrag.
    """
    def __init__(self,name,zpost,mean,cov,rsdrag):
        self.rsdrag = rsdrag
        self.pdf = GaussianPdf(mean,cov)
        Posterior.__init__(self,name,zpost)
    #new shape for mean and values for new covariance matrix

    def constraint(self,DHz,DAz,muz):
        """Calculate -log(prob) for the posterior applied to a set of expansion histories.

        Args:
            DHz(ndarray): Array of DH(zpost) values to use.
            DAz(ndarray): Array of DA(zpost) values to use.
            muz(ndarray): this is no longer the 5log(DL/10pc) but instead 5 log (DL/DH0)

        Returns:
            ndarray: Array of -log(prob) values calculated at each input value.
        """
		#scaling rsdrag by DHz*
		# needs to be fixed as DHz[-1] is not DHz*
        rfid = 149.28
        Hz = 2.99792458e5 /DHz *(self.rsdrag * DHz[-1]/1.9273724E-01) /rfid
        DMz = DAz *rfid /(self.rsdrag * DHz[-1]/1.9273724E-01)
        values = np.hstack([DMz,Hz])
        return self.pdf.get_nlp(values)
