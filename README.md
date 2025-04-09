## puesc Sent RMPD fetcher

### Installation
* [Install `uv` package manager](https://docs.astral.sh/uv/getting-started/installation/)
* Install `python>=3.10` using `uv python` 
  ```shell
  uv python install 3.12
  ```
* Install `rmpd` tool using `uv tool` 
```shell
uv tool install git+https://github.com/o-murphy/rmpd.git --prerelease=allow
```
  
### Upgrade `rmpd` tool
```shell
uv tool upgrade rmpd --prerelease=allow
```

### Usage
```
usage: RMPD [-h] [--dump] [rmpd] [truck] [locator]

positional arguments:
  rmpd        RMPD number
  truck       Truck number
  locator     GeoLocator number

options:
  -h, --help  show this help message and exit
  --dump      Save html to file
```

Example
```shell
rmpd RMPDxxxxxxxxxxxxxx YYYYYYYY ZZZ-ZZZZZZ-Z --dump
```