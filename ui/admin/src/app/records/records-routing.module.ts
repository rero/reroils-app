import { NgModule } from '@angular/core';
import { Routes, RouterModule } from '@angular/router';
import { SearchComponent } from './search/search.component';
import { EditorComponent } from './editor/editor.component';
import { CirculationPolicyComponent } from './custom-editor/circulation-settings/circulation-policy/circulation-policy.component';

const routes: Routes = [
  {
    path: 'circ_policies/new',
    component: CirculationPolicyComponent
  },
  {
    path: 'circ_policies/:pid',
    component: CirculationPolicyComponent
  },
  {
    path: ':recordType/new',
    component: EditorComponent
  },
  {
    path: ':recordType/:pid',
    component: EditorComponent
  },
  {
    path: ':recordType',
    component: SearchComponent
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class RecordsRoutingModule { }
