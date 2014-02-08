import date, datetime, time


def validDate(y, m, d):
  isValid = True
  try:
    d = datetime.date(int(y), int(m), int(d))
  except ValueError as e:
    isValid = False
  return isValid
