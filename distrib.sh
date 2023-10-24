PROJECT_DIRPATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

docker run \
    --rm \
    --workdir='/usr/src/myapp' \
    -v "${PROJECT_DIRPATH}:/usr/src/myapp" \
    python:3.12-bullseye bash -c "pip install -r requirements.txt;
                               pip3 install pyinstaller;
                               pyinstaller script_toir.py \
                               --clean \
                               --distpath=dist/linux/ \
                               --name kk_toir_integration \
                               --onefile -y;
                               chown -R ${UID} dist; "