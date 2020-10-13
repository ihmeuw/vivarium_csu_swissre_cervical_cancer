"""Main application functions for producing model specifications."""
from pathlib import Path

from jinja2 import Template
from loguru import logger

from vivarium_csu_swissre_cervical_cancer import paths, metadata
from vivarium_csu_swissre_cervical_cancer.utilities import sanitize_location


def build_model_specifications(template: str, location: str, output_dir: str):
    """Builds and writes model specifications from a template and location.

    Parameters
    ----------
    template
        String path to the model specification template file.
    location
        Location to generate the model specification for. Must be a
        location configured in the project ``constants/metadata.py`` or ``'all'``
        to generate all model specifications.
    output_dir
        String path to the output directory where the model specification(s)
        will be written.

    Raises
    ------
    ValueError
        If the provided location in not ``'all'`` or is not one of the
        locations configured in the project ``constants/metadata.py``.

    """
    template = Path(template)
    output_dir = Path(output_dir)

    if location == 'all' and len(metadata.LOCATIONS):
        locations = metadata.LOCATIONS
    elif location in metadata.LOCATIONS:
        locations = [location]
    else:
        raise ValueError(f'Make sure you have populated the LOCATIONS list in constants/metadata.py.\n'
                         f'Location must be the string "all" or one of {metadata.LOCATIONS}\n'
                         f'You specified "{location}".\n')

    logger.debug(f'Reading model spec template from {str(template)}.')
    with template.open() as infile:
        jinja_template = Template(infile.read())

    logger.info(f'Writing model spec(s) to "{str(output_dir)}".')

    for location in locations:
        sanitized_location = sanitize_location(location)
        file_path = output_dir / f'{sanitized_location}.yaml'
        with file_path.open('w+') as outfile:
            logger.debug(f'Writing {file_path.name}.')
            rendered_template = jinja_template.render(
                location_proper=location,
                location_sanitized=sanitized_location,
                artifact_directory=paths.ARTIFACT_ROOT,
            )
            outfile.write(rendered_template)
