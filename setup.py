from setuptools import setup

setup(
    name="environment_kernels",
    description="Launch Jupyter kernels installed in environments",
    url="https://github.com/Cadair/jupyter_environment_kernels/",
    author="Stuart Mumford",
    author_email="stuart@cadair.com",
    license="BSD",
    packages=['environment_kernels'],
    include_package_data=True,
    version=1.1,
    classifiers=[
        "Topic :: Utilities",
        "License :: OSI Approved :: BSD License",
    ],
)
