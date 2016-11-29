set -x
echo "Downloading MITIE models..."
wget https://github.com/mit-nlp/MITIE/releases/download/v0.4/MITIE-models-v0.2.tar.bz2
echo "Uncompressing MITIE models..."
tar --no-same-owner -xjf MITIE-models-v0.2.tar.bz2  
echo "Dowloading word2vec model..."
wget https://s3.amazonaws.com/mordecai-geo/GoogleNews-vectors-negative300.bin.gz
echo "Done."
