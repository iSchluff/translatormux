## translator mux prototype

Run
```
podman build -t translatormux .
podman run -it --rm -v `pwd`:/work --workdir /work translatormux
pipenv sync
pipenv run ./main.py
```
