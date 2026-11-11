// Exercise every selection in the offline report without external browser code.
const fs = require('fs');
const vm = require('vm');
const path = require('path');
const elements = {};
for (const id of ['geom','pupil','channel','chart','chartnote','peaktable']) {
  elements[id] = {value:'', innerHTML:'', textContent:'', addEventListener(){}};
}
elements.geom.value='cross_gap1';
elements.pupil.value='disk_r020';
elements.channel.value='port_sum';
const context = vm.createContext({document:{getElementById(id){return elements[id];}}});
vm.runInContext(fs.readFileSync(path.join(__dirname,'report_interactive.js'),'utf8'),context);
let checks=0;
for (const geom of ['ideal','cross_gap1','square_gap2','phase_upper_pi']) {
  for (const pupil of ['disk_r020','disk_r010','disk_r005','disk_r010_y006','disk_r020_edge_y004']) {
    for (const channel of ['port_sum','port_diff','raw_sum']) {
      Object.assign(elements.geom,{value:geom});
      Object.assign(elements.pupil,{value:pupil});
      Object.assign(elements.channel,{value:channel});
      vm.runInContext('render()',context);
      if (!elements.chart.innerHTML.includes('<path') || /NaN|undefined/.test(elements.chart.innerHTML)) {
        throw new Error(`Invalid chart: ${geom},${pupil},${channel}`);
      }
      if (!elements.peaktable.innerHTML.includes('<table>')) throw new Error('Missing data table');
      checks++;
    }
  }
}
console.log(`Report controls rendered successfully for ${checks} structure/pupil/channel selections.`);
