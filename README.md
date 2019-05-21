# GPHistTDE
GP regression code that lead to our TDE mdoel


infer.py runs the GP regression

ex: python infer.py --num-sample 1000000 --hyper-index 0 --hyper-count 625 --hyper-num-h 25 --hyper-num-sigma 25 --growth --dark-energy --output npz_files/test_

This generates 625 npz files, one for each value of the hyperparameter grid


combine.py marginalizes over the hyperparameter grid

ex: combine.py --input npz_files/test_ --output test --number 625

This generates 1 npz file which can then be loaded for plotting


plot.py plots the various posteriors

ex: python plot.py --input test --output plots/test/test_ --nlp --full --zoom
