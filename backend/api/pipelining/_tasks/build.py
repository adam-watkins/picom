from docker.errors import BuildError, APIError

from api import worker_session
from api.models.container import Container, ContainerBuild, ContainerBuildError

from . import docker, utils, dramatiq


@dramatiq.actor(max_retries=0)
def build_container_task(container_id: int):
    print(f"BUILDING CONTAINER: {container_id}")

    with worker_session() as db:
        container = Container.query(db).get(container_id)
        container_build = ContainerBuild(
            container_id=container.id,
            status='building'
        )
        build_path = container.build_abs_path
        container_build.save(db)
        tag = utils.validate_tag(container_build.generate_tag())

    try:
        print('path', build_path)
        print('tag', tag)
        image, build_logs = docker.images.build(
            rm=True, path=build_path, tag=tag)
    except (BuildError, APIError) as e:
        with worker_session() as db:
            container_build.status = 'exited'
            container_build.exit_code = 1
            container_build.save(db)

            ContainerBuildError(
                container_build_id=container_build.id, stderr=str(e)).save(db)
    else:
        with worker_session() as db:
            container_build.status = 'exited'
            container_build.exit_code = 0
            container_build.tag = image.tags[0]
            container_build.save(db)
