# import fish  # We will use fish soon ;)
import progressbar


# class Duck(fish.SwimFishTimeSync, fish.DuckLook):
#     pass


class Balloon(progressbar.ProgressBar):
    def __init__(self, message="Waiting", **kwargs):
        widgets = [
            "%s " % message,
            progressbar.AnimatedMarker(markers='.oO@* '),
            progressbar.Timer(format=" %s")
        ]
        super(Balloon, self).__init__(widgets=widgets, maxval=600, **kwargs)
        self.start()
