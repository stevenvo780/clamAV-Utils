# clamav_scanner/gui/gui_utils.py

import multiprocessing

def update_jobs(app):
    total_cpus = multiprocessing.cpu_count()
    nucleos_libres = app.nucleos_libres.get()
    app.jobs.set(max(1, total_cpus - nucleos_libres))
