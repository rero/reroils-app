/// <reference types="Cypress" />
/*

RERO ILS
Copyright (C) 2021 RERO

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.

*/
before(function () {
  cy.fixture('documents').then(function (documents) {
    this.documents = documents;
  });
  cy.fixture('users').then(function (userData) {
    this.users = userData;
  });
  cy.fixture('common').then(function (commonData) {
    this.common = commonData;
  });
})

describe('Create a document with all simple fields', function() {
  let documentPid;
  let documentTitleSuffix = ' ' + cy.getCurrentDateAndHour();
  before('Login as a professional and create a simple document', function() {
    this.spock = this.users.librarians.spock;
    // Login as librarian
    cy.adminLogin(this.spock.email, this.common.uniquePwd);
    cy.apiCreateDocument(this.documents.book, documentTitleSuffix);
    cy.get('@getDocumentPid').then((pid) => {
      documentPid = pid;
    });
   });

  beforeEach('Preserve logged user', function() {
    // Preserve authentication information between the tests
    Cypress.Cookies.preserveOnce('session');
  });

  after('Clean data: remove document', function() {
    // Delete document
    cy.apiDeleteResources('documents', 'pid:"'+ documentPid + '"');
    cy.logout();
    cy.log('End of the test');
  });

  it('Add fields', function() {
    /**
     * Fields tested:
     * bibliographic formats
     * extent
     * dimensions
     * subjects
     * color content
     * abstract
     * copyright date
     * duration
     * illustrative content
     * production method
     * translated from
     * titles proper
     */
    cy.intercept('/api/permissions/documents/' + documentPid).as('getDocPermission');
    // Go to document editor
    cy.visit('/professional/records/documents/edit/' + documentPid);
    cy.wait('@getDocPermission');
    // Remove provision activity statement
    cy.get('#provisionActivity-0-statement-remove-button').click();
    // Add bibliographic format
    cy.get('#addField').type('Bibliographic formats{enter}');
    cy.get('#bookFormat-0').select(this.documents.book.format);
    // Add extent
    cy.get('#add-field-4').click();
    cy.get('#extent').type(this.documents.book.extent);
    // Add dimensions
    cy.get('#add-field-2').click();
    cy.get('#dimensions-0').type(this.documents.book.dimensions[0]);
    // Add subject
    cy.get('#add-field-7').click();
    cy.get('#subjects-0').type(this.documents.book.subjects[0]);
    cy.get('#field-subjects-0 button').click();
    cy.get('#subjects-1').type(this.documents.book.subjects[1]);
    // Add color contents
    cy.get('#addField').type('Color contents{enter}');
    cy.get('#colorContent-0').select(this.documents.book.colorContent[0].value);
    // Add copyright date
    cy.get('#addField').type('Copyright dates{enter}');
    cy.get('#copyrightDate-0').type(this.documents.book.copyrightDate[0]);
    // Add duration
    cy.get('#addField').type('Durations{enter}');
    cy.get('#duration-0').type(this.documents.book.duration[0]);
    // Add illustrative content
    cy.get('#addField').type('Illustrative contents{enter}');
    cy.get('#illustrativeContent-0').type(this.documents.book.illustrativeContent[0]);
    // Add production method
    cy.get('#addField').type('Production methods{enter}');
    cy.get('#productionMethod-0').select(this.documents.book.productionMethod[0].value);
    // Add translated from
    cy.get('#addField').type('Translated from{enter}');
    cy.get('#translatedFrom-0').select(this.documents.book.translatedFrom[0]);
    // Add title proper
    cy.get('#addField').type('Uniform title{enter}');
    cy.get('#titlesProper-0').type(this.documents.book.titlesProper[0]);

    // Save
    cy.get('#editor-save-button').click();

    // Check document detail view
    cy.checkDocumentEssentialFields(this.documents.book);
    cy.get('#doc-extent').should('contain', this.documents.book.extent);
    cy.get('#doc-subject-0').should('contain', this.documents.book.subjects[0]);
    cy.get('#doc-subject-1').should('contain', this.documents.book.subjects[1]);
    cy.get('#doc-language-0').should('contain', this.documents.book.translatedFrom[0]);
    cy.get('#doc-copyright-date').should('contain', this.documents.book.copyrightDate[0]);
    cy.get('#doc-duration').should('contain', this.documents.book.duration[0]);
    cy.get('#doc-illustrative-content').should('contain', this.documents.book.illustrativeContent[0]);
    cy.get('#doc-colors').should('contain', this.documents.book.colorContent[0].value);
    cy.get('#doc-production-method').should('contain', this.documents.book.productionMethod[0].code);
    cy.get('#doc-book-format').should('contain', this.documents.book.format);
    cy.get('#doc-dimension').should('contain', this.documents.book.dimensions[0]);
    cy.get('#doc-uniform-title').should('contain', this.documents.book.titlesProper[0]);
  });
})
