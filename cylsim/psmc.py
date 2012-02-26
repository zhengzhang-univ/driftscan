import numpy as np

from cylsim import psestimation

from simulations.foregroundmap import matrix_root_manynull


def sim_skyvec(trans):
    """Simulate a set of alm(\nu)'s for a given m.

    Generated as if m=0. For greater m, just ignore entries for l < abs(m).

    Parameters
    ----------
    trans : np.ndarray
        Transfer matrix generated by `block_root` from a a particular C_l(z,z').

    Returns
    -------
    gaussvars : np.ndarray
       Vector of alms.
    """
    
    lside = trans.shape[0]
    nfreq = trans.shape[1]

    matshape = (lside, nfreq)

    gaussvars = (np.random.standard_normal(matshape)
                 + 1.0J * np.random.standard_normal(matshape)) / 2.0**0.5

    for i in range(lside):
        gaussvars[i] = np.dot(trans[i], gaussvars[i])

    return gaussvars.T.copy()
        

def block_root(clzz):
    """Blah.
    """

    trans = np.zeros_like(clzz)

    for i in range(trans.shape[0]):
        trans[i] = matrix_root_manynull(clzz[i], truncate=False)

    return trans
    

class PSMonteCarlo(psestimation.PSEstimation):
    """An extension of the PSEstimation class to support estimation of the
    Fisher matrix via Monte-Carlo simulations.

    This should be significantly faster when including large numbers of eigenmodes.

    Attributes
    ----------
    nswitch : integer
        The threshold number of eigenmodes above which we switch to Monte-Carlo
        estimation.
    nsamples : integer
        The number of samples to draw from each band.
    """
    
    nsamples = 100
    nswitch = 200

    def genbands(self):
        """Override genbands to make it generate the transformation matrices for
        drawing random samples.
        """
        psestimation.PSEstimation.genbands(self)

        print "Generating transforms..."
        self.transarray = [block_root(clzz[0, 0]) for clzz in self.clarray]



    def get_vecs(self, mi, bi, scale=False):
        """Get a set of random samples from the specified band `bi` for a given
        `mi`.
        """
        evsims = np.zeros((self.nsamples, self.num_evals(mi)), dtype=np.complex128)

        for i in range(self.nsamples):
            skysim = sim_skyvec(self.transarray[bi])
            evsims[i] = self.kltrans.project_sky_vector_forward(mi, skysim, threshold=self.threshold)

        if scale:
            #evsims = (evsims - evsims.mean(axis=0)[np.newaxis, :]) / (1.0 + evals[np.newaxis, :])**0.5
            evals = self.kltrans.modes_m(mi, threshold=self.threshold)[0]
            evsims = evsims / (1.0 + evals[np.newaxis, :])**0.5

        return evsims


    def gen_vecs(self, mi):
        """Generate a cache of sample vectors for each bandpower.
        """

        self.vec_cache = [ self.get_vecs(mi, bi, scale=True) for bi in range(len(self.clarray))]


    def makeproj_mc(self, mi, bi):
        """Estimate the band covariance from a set of samples.
        """
        evsims = self.get_vecs(mi, bi)
        #evsims = evsims - evsims.mean(axis=0)[np.newaxis, :]
        return np.dot(evsims.T.conj(), evsims) / (self.nsamples - 1.0)


    def fisher_m_mc(self, mi):
        """Calculate the Fisher Matrix by Monte-Carlo.
        """
            
        nbands = len(self.bands) - 1
        fab = np.zeros((nbands, nbands), dtype=np.complex128)

        if self.num_evals(mi) > 0:
            print "Making fisher (for m=%i)." % mi

            self.gen_vecs(mi)

            ns = self.nsamples

            for ia in range(nbands):
                # Estimate diagonal elements (including bias correction)
                va = self.vec_cache[ia]
                tmat = np.dot(va, va.T.conj())
                fab[ia, ia] = (np.sum(np.abs(tmat)**2) / ns**2 - np.trace(tmat)**2 / ns**3) / (1.0 - 1.0 / ns**2)

                # Estimate diagonal elements
                for ib in range(ia):
                    vb = self.vec_cache[ib]
                    fab[ia, ib] = np.sum(np.abs(np.dot(va, vb.T.conj()))**2) / ns**2
                    fab[ib, ia] = np.conj(fab[ia, ib])
            
        else:
            print "No evals (for m=%i), skipping." % mi

        return fab


    def fisher_m(self, mi):
        """Calculate the Fisher Matrix for a given m.

        Decides whether to use direct evaluation or Monte-Carlo depending on the
        number of eigenvalues required.
        """
        if self.num_evals(mi) < self.nswitch:
            return super(PSMonteCarlo, self).fisher_m(mi)
        else:
            return self.fisher_m_mc(mi)
        
        