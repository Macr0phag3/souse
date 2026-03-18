# python -m pip install --upgrade build twine

rm -rf dist build *.egg-info

python -m build
python -m twine check dist/*

python -m twine upload --repository testpypi dist/*

python -m twine upload dist/*
