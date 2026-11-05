"""Export the independently installable pack, with its original attribution."""
import argparse
import json
from pathlib import Path
import zipfile

from package import PACK, bundle


def main():
    parser=argparse.ArgumentParser(description='导出配置包和完整来源资料')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    content=bundle()
    target=args.output or PACK/'exports'/('lasers-and-feelings-'+content['manifest']['version']+'.zip')
    if target.exists():
        parser.error('输出已存在，请指定新路径；不会覆盖已有文件')
    target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('bundle.json',json.dumps(content,ensure_ascii=False,indent=2))
        for folder in ['config','rules','flows','ui','sources','docs','tools','tests']:
            for file in (PACK/folder).rglob('*'):
                if file.is_file() and '__pycache__' not in file.parts and 'output' not in file.relative_to(PACK).parts:
                    archive.write(file,file.relative_to(PACK).as_posix())
        for name in ['README.md','manifest.json','start.ps1','启动激光与情感.exe','LICENSE.md','.gitignore']:
            archive.write(PACK/name,name)
    print(str(target.resolve()))


if __name__=='__main__':
    main()
