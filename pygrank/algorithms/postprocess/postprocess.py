import warnings


class Tautology:
    """ Returns ranks as-are.

    This class can be used as a baseline against which to compare other rank post-processing algorithms
    (e.g. those of this package).
    """

    def __init__(self):
        pass

    def transform(self, ranks):
        return ranks

    def rank(self, _, personalization):
        return personalization


class Normalize:
    """ Normalizes ranks by dividing with their maximal value."""

    def __init__(self, ranker=None, method="max"):
        """ Initializes the class with a base ranker instance.

        Attributes:
            ranker: The base ranker instance. A Tautology() ranker is created if None (default) was specified.
            method: Divide ranks either by their "max" (default) or by their "sum"

        Example:
            >>> from pygrank.algorithms.postprocess import Threshold
            >>> G, seed_values, algorithm = ...
            >>> algorithm = Threshold(0.5, algorithm) # sets ranks >= 0.5 to 1 and lower ones to 0
            >>> ranks = algorithm.rank(G, seed_values)

        Example (same outcome, quicker one-time use):
            >>> from pygrank.algorithms.postprocess import Normalize
            >>> G, seed_values, algorithm = ...
            >>> ranks = Normalize(0.5).transform(algorithm.rank(G, seed_values))
        """
        if ranker is not None and not callable(getattr(ranker, "rank", None)):
            ranker, method = method, ranker
            if not callable(getattr(ranker, "rank", None)):
                ranker = None
        self.ranker = Tautology() if ranker is None else ranker
        self.method = method

    def _transform(self, ranks):
        if self.method == "max":
            max_rank = max(ranks.values())
        elif self.method == "sum":
            max_rank = sum(ranks.values())
        else:
            raise Exception("Can only normalize towards max or sum")
        return {node: rank / max_rank for node, rank in ranks.items()}

    def transform(self, ranks, *args, **kwargs):
        return self._transform(self.ranker.transform(ranks, *args, **kwargs))

    def rank(self, G, personalization, *args, **kwargs):
        return self._transform(self.ranker.rank(G, personalization, *args, **kwargs))


class Ordinals:
    """ Converts ranking outcome to ordinal numbers.

    The highest rank is set to 1, the second highest to 2, etc.
    """

    def __init__(self, ranker=None):
        """ Initializes the class with a base ranker instance.

        Attributes:
            ranker: Optional. The base ranker instance. A Tautology() ranker is created if None (default) was specified.
        """
        self.ranker = Tautology() if ranker is None else ranker

    def _transform(self, ranks):
        return {v: ord+1 for ord, v in enumerate(sorted(ranks, key=ranks.get, reverse=False))}

    def transform(self, ranks, *args, **kwargs):
        return self._transform(self.ranker.transform(ranks, *args, **kwargs))

    def rank(self, G, personalization, *args, **kwargs):
        return self._transform(self.ranker.rank(G, personalization, *args, **kwargs))


class Threshold:
    """ Converts ranking outcome to binary values based on a threshold value."""

    def __init__(self, threshold="gap", ranker=None):
        """ Initializes the Threshold postprocessing scheme.

        Attributes:
            threshold: Optional. The minimum numeric value required to output rank 1 instead of 0. If "gap" (default)
                then its value is automatically determined based on the maximal percentage increase between consecutive
                ranks.
            ranker: Optional. The base ranker instance. A Tautology() ranker is created if None (default) was specified.

        Example:
            >>> from pygrank.algorithms.postprocess import Threshold
            >>> G, seed_values, algorithm = ...
            >>> algorithm = Threshold(0.5, algorithm) # sets ranks >= 0.5 to 1 and lower ones to 0
            >>> ranks = algorithm.rank(G, seed_values)

        Example (same outcome):
            >>> from pygrank.algorithms.postprocess import Threshold
            >>> G, seed_values, algorithm = ...
            >>> ranks = Threshold(0.5).transform(algorithm.rank(G, seed_values))
        """
        if ranker is not None and not callable(getattr(ranker, "rank", None)):
            ranker, threshold = threshold, ranker
            if not callable(getattr(ranker, "rank", None)):
                ranker = None
        self.ranker = Tautology() if ranker is None else ranker
        self.threshold = threshold
        if threshold == "gap":
            warnings.warn("gap-determined threshold is still under development (its implementation may be incorrect)", stacklevel=2)

    def _transform(self, ranks, G):
        threshold = self.threshold
        if threshold == "none":
            return ranks
        if threshold == "gap":
            ranks = {v: ranks[v] / G.degree(v) for v in ranks}
            max_diff = 0
            threshold = 0
            prev_rank = 0
            for v in sorted(ranks, key=ranks.get, reverse=True):
                if prev_rank > 0:
                    diff = (prev_rank - ranks[v]) / prev_rank
                    if diff > max_diff:
                        max_diff = diff
                        threshold = ranks[v]
                prev_rank = ranks[v]
        return {v: 1  if ranks[v] >= threshold else 0 for v in ranks.keys()}

    def transform(self, ranks, *args, **kwargs):
        return self._transform(self.ranker.transform(ranks, *args, **kwargs))

    def rank(self, G, personalization, *args, **kwargs):
        return self._transform(self.ranker.rank(G, personalization, *args, **kwargs))


class Sweep:
    def __init__(self, ranker, uniform_ranker=None):
        self.ranker = ranker
        self.uniform_ranker = ranker if uniform_ranker is None else uniform_ranker

    def rank(self, G, personalization, *args, **kwargs):
        ranks = self.ranker.rank(G, personalization, *args, **kwargs)
        uniforms = self.uniform_ranker.rank(G, {v: 1 for v in G}, *args, **kwargs)
        return {v: ranks[v]/uniforms[v] for v in G}
