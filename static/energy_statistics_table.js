$(function () 
{
  var first_time = true;
  alert("This function ran!");

  // Theoretically data_url should be defined.
  alert("data_url is: " + data_url);

  function refreshdata_json_cb(data) 
  {
    // Given new data from the server, update the table

    // TODO: what if somehow we get no results and it's not the 
    // first time?
    if (first_time && data.no_results) 
    {
      alert("we received no data :(");
      return; // TODO: tell the user what happened?
    }

    // When this function is first called, it is expected that 
    // data_url was defined previously (before loading this file).
    data_url = data.data_url;
    alert("we have a data_url which is: " + data_url);
  }

  function refreshdata() 
  {
    $.getJSON(data_url, refreshdata_json_cb);
  }

  // Start getting data!
  refreshdata();

})();