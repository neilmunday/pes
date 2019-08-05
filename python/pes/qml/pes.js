function addLeadingZero(x) {
  if (x >= 10){
    return x;
  }
  return "0" + x;
}

function getTime(){
  var d = new Date();
  var s = '';
  var days = d.getDate();
  var month = d.getMonth() + 1;
  var year = d.getYear() + 1900;
  var hours = d.getHours();
  var mins = d.getMinutes();
  var secs = d.getSeconds();

  return addLeadingZero(hours) + ':' + addLeadingZero(mins) + ':' + addLeadingZero(secs) + ' ' + addLeadingZero(days) + '/' + addLeadingZero(month) + '/' + year;
}
