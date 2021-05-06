..
    RERO ILS
    Copyright (C) 2018-2021 RERO
	Copyright (C) 2018-2021 UCLouvain

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, version 3 of the License.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
    GNU Affero General Public License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program. If not, see <http://www.gnu.org/licenses/>.

==================================================
 `RERO ILS <https://github.com/rero/rero-ils>`_
==================================================

.. image:: https://github.com/rero/rero-ils/workflows/build/badge.svg
        :alt: Github actions status
        :target: https://github.com/rero/rero-ils/actions?query=workflow%3Abuild

.. image:: https://img.shields.io/coveralls/rero/rero-ils.svg
        :target: https://coveralls.io/r/rero/rero-ils

.. image:: https://img.shields.io/github/tag/rero/rero-ils.svg
        :alt: Release Number
        :target: https://github.com/rero/rero-ils/releases/latest

.. image:: https://img.shields.io/badge/License-AGPL%20v3-blue.svg
        :alt: License
        :target: http://www.gnu.org/licenses/agpl-3.0.html

.. image:: https://img.shields.io/gitter/room/rero/reroils.svg
        :alt: Gitter room
        :target: https://gitter.im/rero/reroils

.. image:: https://hosted.weblate.org/widgets/rero_plus/-/rero-ils/svg-badge.svg
        :alt: Translation status
        :target: https://hosted.weblate.org/engage/rero_plus/?utm_source=widget

*Copyright (C) 2018-2021 RERO*, *Copyright (C) 2018-2021 UCLouvain*

Table of Content
----------------

1. `What is RERO ILS?`_
2. `Who’s going to run RERO ILS, in which context?`_
3. `What does RERO ILS?`_
4. `How to install RERO ILS?`_
5. `How to contribute to RERO ILS?`_
6. `The RERO ILS ecosystem`_

What is RERO ILS?
-----------------

`RERO ILS`_ is an ILS developed by `RERO`_. ILS stands for
`Integrated Library Service`_, which can be translated into “a software that
helps libraries to do their daily tasks”, such as enriching library collections
through the acquisition of documents (books, ebooks, articles, pictures,
movies, games, video games, music, music score, and so on), describing them to
facilitate their identification and their retrieval through the search feature
of the catalog, and of course, providing them to readers, usually called
patrons.

`RERO`_ is a Swiss network of libraries, which is undergoing a major
restructuring, in the framework of the `rero21`_ project. For this project,
RERO needs to replace the old proprietary ILS software that is in use and to
redirect its effort mainly towards public, school and heritage libraries. Based
on its 30 years experience running a library network and all the scripts and
side processes that had to be developed around the commercial product, the
*centrale* (the team of librarians and developers that maintain the network at
its central office) is developing an open source ILS, to be able to address all
the future needs of its partners and customers.

Using the same legacy commercial ILS and interested by the project for its own
needs, the libraries of `UCLouvain`_, `UNamur`_ and `U.Saint-Louis Brussels`_
are contributing to the development of RERO ILS, and are well integrated into
the RERO SCRUM processes.

RERO ILS is based on a development framework for information systems such as
library management (ILS), institutional repositories, digital libraries and
research data management. This framework, developed at `CERN`_ is called
`Invenio`_.

Who’s going to run RERO ILS, in which context?
----------------------------------------------

RERO ILS is a *free software*, which means that you are free to copy, modify
and distribute it, as long as you respect the `AGPLv3`_ license.

RERO ILS allows a team of library professionals and IT people to provide
an ILS *as a Service* to several library networks through a unique
instance (installation) of the software. This is what we call the
*consortial model feature*. Each network, or *organisation* as we named it, is
isolated from the others, but they all share a union catalog, which helps
patrons discover documents and allows librarian to share cataloguing effort.
Inside an organisation, libraries share most resources and parameters, without
preventing specific configurations or restricting the edition of some resources
to a single library.

RERO ILS is very much adapted to the needs of the RERO *centrale* and its
partners and customers, both present and future. RERO provides its ILS *as a
service* to every interested library or organisation. But the software can be
deployed by other institutions, in different contexts as well, if they can
afford the required effort on configuration or development. It could be run for
a standalone library in an instance with only one organisation with a single
library, but RERO ILS is not designed for that use case. It’s powerful, thus
complex.

What does RERO ILS?
---------------------

*Present*

RERO ILS is still under heavy development, but it already provides a *public
interface* for visitors and patrons. This interface mainly includes searching
features within the catalog, along with a set of other patron-oriented
functionalities. It has multiple views, the *union catalog* view, with all the
documents of all the organisations, and a view for each organisation with all
the documents belonging to one of its libraries. Patrons are able to place
requests on desired items, check their profile, see the list of borrowed items
and so on.

Librarians use a *professional interface*, in which they perform their daily
tasks:

-  Administering organisations, libraries, circulation policies.
-  Managing users: patrons, but also librarians and system librarians.
-  Performing circulation tasks, such as checkins, checkouts, renewals,
   managing requests.
-  Managing patron fees (overdue, subscriptions).
-  Searching for documents, describing documents, linking authorities to
   documents, importing metadata in MARC format, adding items to
   documents.
-  Setting serials patterns, receiving issues.
-  Managing acquisition budgets, vendor information, orders and invoices.

*Future*

The first major release of RERO ILS (``v1.0.0``) is planned for the end of 2020,
and to be live in production in the first half of 2021, with the minimal
features needed to run real world networks. Then, the development of RERO ILS
will go on to reach full ILS functions, but it will never ends, as long as a
software can always be improved and adapted to the need of its users.

How to install RERO ILS?
------------------------

The installation process is described in a `specific file`_.

For a development environment you can check another
`documentation`_.

Check the `ecosystem`_ section.

How to contribute to RERO ILS?
------------------------------

You can test the latest release on
`ils.test.rero.ch`_.

If you have questions, you can ask the development team on `Gitter`_.

You can also `open an issue`_.

You can help translating the software on `Weblate`_.

To contribute to the code itself, please check the
`contributing recommandations`_.

The RERO ILS ecosystem
----------------------

Three GitHub repositories for RERO ILS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The `rero-ils GitHub project`_ contains the main projet for RERO ILS, basically
providing the backend. To work on the frontend of the project, you also need
`rero-ils-ui`_, which is based on `ng-core`_.

MEF
^^^

The `MEF`_ (*Multilingual Entity File*), provides authorities (or entities) to
RERO ILS, in two languages (for now, but others are planned): French and
German. This is used to link documents to controlled descriptions of authors
and subjects. MEF aggregates several authority files, such as `IdRef`_, `BnF`_,
`GND`_ and `RERO <http://data.rero.ch/>`__. These authority files are then
aligned through `VIAF`_, thus providing multilingual authorities. As of May
2020, only physical persons records have been included in MEF, the other entity
types are in preparation.

As a result, in order to run RERO ILS, you need to either use our
`public MEF server <https://mef.test.rero.ch>`__, or run your own.

RERO EBOOKS
^^^^^^^^^^^

RERO ILS customers make use of 3rd-party ebook commercial platforms. A
dedicated server has been set up for harvesting ebook metadata from those
platforms, convert them to RERO ILS's own data model. RERO ILS harvests
our ebooks server, importing the metadata into the union catalog, assigning
each ebook to the corresponding subscribing libraries.

This server is not publicly accessible. The source code is available on GitHub:
`rero-ebooks`_.

You need to prevent your RERO ILS instance to harvest RERO's ebooks server, but
you can run your own ebooks server.

.. References:
.. _`What is RERO ILS?`: #what-is-rero-ils
.. _`Who’s going to run RERO ILS, in which context?`: #whos-going-to-run-rero-ils-in-which-context
.. _`What does RERO ILS?`: #what-does-rero-ils
.. _`How to install RERO ILS?`: #how-to-install-rero-ils
.. _`How to contribute to RERO ILS?`: #how-to-contribute-to-rero-ils
.. _`The RERO ILS ecosystem`: #the-rero-ils-ecosystem
.. _`RERO ILS`: https://github.com/rero/rero-ils
.. _`RERO`: https://rero.ch
.. _`Integrated Library Service`: https://en.wikipedia.org/wiki/Integrated_library_system
.. _`rero21`: https://rero21.ch/en/about/
.. _`UCLouvain`: https://uclouvain.be
.. _`UNamur`: https://www.unamur.be
.. _`U.Saint-Louis Brussels`: https://www.usaintlouis.be
.. _`CERN`: https://home.cern
.. _`Invenio`: https://inveniosoftware.org
.. _`AGPLv3`: https://www.gnu.org/licenses/agpl-3.0.html
.. _`specific file`: INSTALL.rst
.. _`documentation`: https://github.com/rero/developer-resources/blob/master/rero-instances/rero-ils/dev_installation.md
.. _`ecosystem`: #the-rero-ils-ecosystem
.. _`ils.test.rero.ch`: https://ils.test.rero.ch
.. _`open an issue`: https://github.com/rero/rero-ils/issues/new
.. _`Weblate`: https://hosted.weblate.org/projects/rero_plus/#information
.. _`Gitter`: https://gitter.im/rero/reroils
.. _`contributing recommandations`: https://github.com/rero/rero-ils/blob/dev/CONTRIBUTING.rst
.. _`rero-ils GitHub project`: https://github.com/rero/rero-ils
.. _`rero-ils-ui`: https://github.com/rero/rero-ils-ui
.. _`ng-core`: https://github.com/rero/ng-core
.. _`MEF`: https://github.com/rero/rero-mef
.. _`IdRef`: https://www.idref.fr/
.. _`BnF`: https://www.bnf.fr/fr/donnees-autorite-bnf
.. _`GND`: https://www.dnb.de/DE/Professionell/Standardisierung/GND/gnd_node.html
.. _`VIAF`: https://viaf.org
.. _`public MEF server`: https://mef.test.rero.ch
.. _`rero-ebooks`: https://github.com/rero/rero-ebooks
