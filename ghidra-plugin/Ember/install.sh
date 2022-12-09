EXTENSIONS_PATH="${GHIDRA_EXTENSIONS_DIR}"
EXTENSION_DIR="${EXTENSIONS_PATH}/Ember"
DIST_PATH=dist
DATE=`date +"%Y%m%d"`
FILE="ghidra_10.1.4_PUBLIC_${DATE}_Ember.zip"
SRC_FILE="${DIST_PATH}/${FILE}"
DST_FILE="${EXTENSIONS_PATH}/${FILE}"


if [ ! -e ${SRC_FILE} ];
then
    echo "ERROR: run gradle"
    exit
fi

if [ -e ${DST_FILE} ];
then
    echo "deleting ${DST_FILE}"
    rm ${DST_FILE}
fi

if [ -d ${EXTENSION_DIR} ];
then
    echo "deleting ${EXTENSION_DIR}"
    rm -rf ${EXTENSION_DIR}
fi

echo "copying ${SRC_FILE} to ${DST_FILE}"
cp ${SRC_FILE} ${DST_FILE}

echo "unzipping"
unzip ${DST_FILE} -d $EXTENSIONS_PATH
