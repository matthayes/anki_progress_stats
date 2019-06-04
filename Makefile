init:
	pip install pipenv --upgrade
	pipenv install --dev --skip-lock

test:
	pipenv run py.test

flake8:
	pipenv run flake8 --ignore=E501

release_anki20:
	./release_anki20.sh

release_anki21:
	./release_anki21.sh