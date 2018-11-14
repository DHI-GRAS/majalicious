# majalicious

Run MAJA V1 on Sentinel 2 data by creating a lot of symlinks

## Dead

NB: MAJA V1 does not work for data past 6 November 2018, where [Copernicus changed L1C format](https://scihub.copernicus.eu/news/News00409). :boom:


## Purpose

This little script automates the processing of Sentinel 2 timeseries with MAJA V1.
It indexes by date all L1C and MAJA-produced L2A products in the folders you provide
and creates symlinks to the ones MAJA needs to run in L2NOMINAL or L2BACKWARD mode.

This way, you e.g. always have the most recent L2A product for the current L1C product
you are processing and you do not need to move any files around when starting to process
a new scene.

Don't worry, it's not malicious. It's majalicious!


## Building

```bash
docker build -t maja
```

## Running

To see the full interface, run

```bash
docker run maja
```

For an actual run, you need to mount the input and auxillary data 
into the docker container.
The default is that you have, inside the container, a folder `/maja-aux`
with the following contents:

```
/maja-aux
  userconf
  GIPP
  DTM/{tile}
```
If you follow this pattern, you can omit the `--src-userconf`, `--src-gipp`, and `--src-dtm` flags. 

Furthermore, you need to provide a `--src-input` directory that contains your `.SAFE` input files
and a `--dst-output` directory for the L2A output.

The `--dst-work-root` directory must be inside the container (i.e. not on a mounted resource) for 
the symlinking to work.

A full example command is the following:

```bash
docker run -v /my/maja/aux:/maja-aux -v /my/maja/data:/maja-data maja --src-input /maja-data/input --dst-output /maja-data/output --tile 32UNG
```

## Docs

This script is a re-implementation of the recipes at https://github.com/olivierhagolle/Start_maja

Please consult that repo for more information on why things are done this way.
