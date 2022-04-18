// App initialization code goes here

$(() => {
  $('#street_search').autocomplete({
    source: '/streets',
    minLength: 2,
    focus(event, ui) {
      $('#street_search').val(ui.item.label);
      return false;
    },
    select(event, ui) {
      $('#street_search').val(ui.item.label);
      $('#street_search-id').val(ui.item.id);
      return false;
    },
  })
    .autocomplete('instance')._renderItem = function (ul, item) {
      return $('<li>')
        .append(`<div>${item.label}</div>`)
        .appendTo(ul);
    };
});
