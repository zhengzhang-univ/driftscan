from cylsim import cylinder

import numpy as np

c1 = cylinder.CylinderTelescope()

bli, fi = np.mgrid[:10,4:7]

#ta1 = c1.transfer_matrices([0, 10], [0, 4])


#ta2 = c1.transfer_matrices(bli, fi)

ta3 = c1.transfer_for_freq(3)