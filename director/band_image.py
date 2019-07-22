import subprocess
from prodict import Prodict as pdict
from typing import Dict

from .constants import (DEF_LABELS, DEFAULT_DOCKERFILE, GIT_IGNORE_POSTFIX)
from .helpers import tar_image_cmd

class BandImageBuilder:
    def __init__(self, img, img_options):
        self.img = img
        self.img_options = img_options
        self.dockerfile = self.img_options.get('dockerfile', DEFAULT_DOCKERFILE)
        # dockerfile_override = f'{dockerfile}.gen{GIT_IGNORE_POSTFIX}'
        # self.dockerfile_generator(
        #     self.img.path, dockerfile, dockerfile_override)
        # self.dockerfile = dockerfile_override

    async def __aenter__(self):
        self.p = subprocess.Popen(
            tar_image_cmd(self.img.path), stdout=subprocess.PIPE)
        return self

    # def dockerfile_generator(self, path, orig, override):
    #     with open(f'{path}/{orig}') as f:
    #         content = f.read()
    #         for k, v in self.img_options.items():
    #             content = content.replace('{' + k + '}', str(v))
    #         with open(f'{path}/{override}', 'w') as nf:
    #             nf.write(content)

    def struct(self):
        return pdict.from_dict({
            'tag': self.img.name,
            'fileobj': self.p.stdout,
            'encoding': 'identity',
            'buildargs': self.img_options.get('buildargs', {}),
            'path_dockerfile': self.dockerfile,
            'nocache': self.img_options.get('nocache', False),
            'forcerm': self.img_options.get('forcerm', True),
            'rm': self.img_options.get('rm', True),
            'pull': self.img_options.get('pull', False),
            'stream': True
        })

    async def __aexit__(self, exception_type, exception_value, traceback):
        self.p.kill()


class BandImage(pdict):
    name: str
    path: str
    key: str
    pos: Dict
    title: str
    base: str
    p: subprocess.Popen
    d: pdict
    meta: pdict

    def __init__(self, *args, **kwargs):
        meta = kwargs.pop('meta', {})

        # meta['protected'] = meta['protected'] if 'protected' in meta else False
        # meta['persistent'] = meta['persistent'] if 'persistent' in meta else False

        name_title = (kwargs.get('key', None) or 'unknown').title().replace('_', ' ').replace('-', ' ')
        kwargs['title'] = kwargs.get('title', name_title)
        kwargs['meta'] = meta

        super().__init__(*args, **kwargs)

    def set_data(self, data):
        self.d = pdict.from_dict(data)
        return self

    @property
    def cmd(self):
        return self.d.Config.Cmd

    @property
    def id(self):
        return self.d.Id

    @property
    def ports(self):
        return list(self.d.ContainerConfig.ExposedPorts.keys())

    def create(self, img_options):
        return BandImageBuilder(self, img_options)
