from doorbeen.core.types.ts_model import TSModel


class DictionaryModifier(TSModel):
    source: dict

    def alter_key_name(self, old_name, new_name):
        if old_name in self.source.keys():
            replaced_key = self.source[old_name]
            self.source.pop(old_name)
            self.source[new_name] = replaced_key
        return self.source
