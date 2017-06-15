# !usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Licensed under a 3-clause BSD license.
#
# @Author: Brian Cherinka
# @Date:   2017-06-10 16:46:40
# @Last modified by:   Brian Cherinka
# @Last Modified time: 2017-06-10 18:54:56

from __future__ import print_function, division, absolute_import
import os
from invoke import Collection, task


DIRPATH = '/home/manga/software/git/manga/marvin'
MODULEPATH = '/home/manga/software/git/modulefiles'


@task
def clean_docs(ctx):
    ''' Cleans up the docs '''
    print('Cleaning the docs')
    ctx.run("rm -rf docs/sphinx/_build")


@task(clean_docs)
def build_docs(ctx):
    ''' Builds the Sphinx docs '''
    print('Building the docs')
    os.chdir('docs/sphinx')
    ctx.run("make html")


@task
def clean(ctx):
    ''' Cleans up the crap '''
    print('Cleaning')
    # ctx.run("rm -rf docs/sphinx/_build")
    ctx.run("rm -rf htmlcov")
    ctx.run("rm -rf build")
    ctx.run("rm -rf dist")


@task(clean)
def deploy(ctx):
    ''' Deploy to pypi '''
    print('Deploying to Pypi!')
    ctx.run("python setup.py sdist bdist_wheel --universal")
    ctx.run("twine register dist/sdss-marvin-*.tar.gz")
    ctx.run("twine register dist/sdss_marvin-*-none-any.whl")
    ctx.run("twine upload dist/*")


@task
def update_default(ctx, path=None, version=None):
    ''' Updates the default version module file'''

    assert version is not None, 'A version is required to update the default version!'
    assert path is not None, 'A path must be specified!'

    # update default version
    f = open('.version', 'r+')
    data = f.readlines()
    data[1] = 'set ModulesVersion "{0}"\n'.format(version)
    f.seek(0, 0)
    f.writelines(data)
    f.close()


@task
def update_module(ctx, path=None, wrap=None, version=None):
    ''' Update a module file '''

    assert version is not None, 'A version is required to update the module file!'
    assert path is not None, 'A path must be specified!'
    print('Setting up module files!')
    os.chdir(path)
    newfile = 'mangawork.marvin_{0}'.format(version) if wrap else version
    oldfile = 'mangawork.marvin_2.1.3' if wrap else 'master'
    searchline = 'marvin' if wrap else 'version'
    ctx.run('cp {0} {1}'.format(oldfile, newfile))
    f = open('{0}'.format(newfile), 'r+')
    data = f.readlines()
    index, line = [(i, line) for i, line in enumerate(data) if 'set {0}'.format(searchline) in line][0]
    data[index] = 'set {0} {1}\n'.format(searchline, version)
    f.seek(0, 0)
    f.write(data)
    f.close()

    # update the default version
    update_default(ctx, path=path, version=newfile)


@task
def update_git(ctx, version=None):
    ''' Update the git package at Utah '''
    assert version is not None, 'A version is required to checkout a new git repo!'
    print('Checking out git tag {0}'.format(version))
    verpath = os.path.join(DIRPATH, version)
    # checkout and setup new git tag
    os.chdir(DIRPATH)
    ctx.run('git clone https://github.com/sdss/marvin.git {0}'.format(version))
    os.chdir(verpath)
    ctx.run('git checkout {0}'.format(version))
    ctx.run('git submodule update --init --recursive')


@task
def update_current(ctx, version=None):
    ''' Update the current symlink '''
    assert version is not None, 'A version is required to update the current symlink!'
    # reset the current symlink
    os.chdir(DIRPATH)
    ctx.run('rm current')
    ctx.run('ln -s current {0}'.format(version))


@task
def setup_utah(ctx, version=None):
    ''' Setup the package at Utah '''
    assert version is not None, 'A version is required to setup Marvin at Utah!'

    # update git
    update_git(ctx, version=version)

    # update_current
    update_current(ctx, version=version)

    # update modules
    marvin = os.path.join(MODULEPATH, 'marvin')
    wrap = os.path.join(MODULEPATH, 'wrapmarvin')
    update_module(ctx, path=marvin, version=version)
    update_module(ctx, path=wrap, wrap=True, version=version)

    # restart the new marvin
    ctx.run('stopmarvin')
    ctx.run('module switch wrapmarvin wrapmarvin/mangawork.marvin_{0}'.format(version))
    ctx.run('startmarvin')


ns = Collection(clean, deploy, setup_utah)
docs = Collection('docs')
docs.add_task(build_docs, 'build')
docs.add_task(clean_docs, 'clean')
ns.add_collection(docs)