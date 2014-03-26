from pyramid.config import Configurator

def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    config = Configurator(settings=settings)
    # adding a Translation Directory
    config.add_translation_dirs('vpt.transformer:locale/')
    config.add_static_view('static', 'static', cache_max_age=3600)
    # publish transforms directory to download transformed files
    config.add_static_view('transforms', 'transforms', cache_max_age=3600)
    # home view
    config.add_route('home', '/')
    config.scan()
    return config.make_wsgi_app()
