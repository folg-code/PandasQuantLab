import pandas as pd
import config

def trim_all_dataframes(self):
    start_time = pd.to_datetime(config.TIMERANGE["start"], utc=True)

    for attr_name, attr_value in self.__dict__.items():
        if isinstance(attr_value, pd.DataFrame) and 'time' in attr_value.columns:
            try:
                # Konwersja na tz-aware UTC, jeśli tz-naive
                if attr_value['time'].dt.tz is None:
                    attr_value['time'] = attr_value['time'].dt.tz_localize('UTC')

                trimmed_df = attr_value[attr_value['time'] >= start_time]
                setattr(self, attr_name, trimmed_df)
            except Exception as e:
                print(f"Błąd przy przycinaniu {attr_name}: {e}")