// Timedeltas in ms
var one_min = 1000*60
var ten_min = 1000*600
var one_hr = 1000*60*60
var four_hrs = 1000*60*60*4
var half_day = 1000*60*60*12
var one_day = 1000*60*60*24
var one_week = 1000*60*60*24*7
var one_month = 1000*60*60*24*31
var one_year = 1000*60*60*24*366

// Extra timedeltas:
var ten_sec = 1000*10
var five_sec = 1000*5
var thirty_sec = 1000*30
var two_min = 1000*60*2
var thirty_min = 1000*60*30
var two_hrs = 1000*60*60*2

// Label format strings:
var hr_min_sec = '%l:%M:%S%P'
var hr_min = '%l:%M%p'
var hr_min_date = '%l:%M%p,<br>%m/%e/%y'
var full_date = '%m/%e/%y'
var month_yr = '%b, \'%y'
var year_month = '%m/%Y'

// Takes in the difference in start/end times (in ms) of
// a graph and returns 
// [major tick res, minor tick res, major tick label]
function tickhelper(timedelta)
{
    if (timedelta <= one_min) { return [ten_sec, five_sec, hr_min_sec]; }
    else if (timedelta <= ten_min) { return [one_min, thirty_sec, hr_min]; }
    else if (timedelta <= one_hr) { return [ten_min, two_min, hr_min]; }
    else if (timedelta <= four_hrs) { return [thirty_min, ten_min, hr_min]; }
    else if (timedelta <= half_day) { return [two_hrs, thirty_min, hr_min]; }
    else if (timedelta <= one_day) { return [four_hrs, one_hr, hr_min_date]; }
    else if (timedelta <= one_week) { return [one_day, four_hrs, full_date]; }
    else if (timedelta <= one_month) { return [one_week, one_day, full_date]; }
    else if (timedelta <= one_year) { return [one_month, one_week, month_yr]; }
    else { return [one_year, one_month, year_month]; }
}
