init:
	pip install -r requirements.txt

test:
	py.test

flake8:
	flake8 --ignore=E501

release_anki20:
	./release_anki20.sh

release_anki21:
	./release_anki21.sh